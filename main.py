import os
import base64
import json
import threading
from flask import Flask
import telebot
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Initialize Flask for Render Health Checks
app = Flask(__name__)

@app.route('/health')
def health_check():
    return {"status": "ok", "service": "ca-study-bot"}, 200

# 2. Configuration from Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
B64_CREDS = os.getenv("GOOGLE_CREDENTIALS_JSON")

# Initialize Bot and AI
bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

# 3. Google Sheets Setup
def get_sheets_client():
    if not B64_CREDS:
        return None
    try:
        creds_dict = json.loads(base64.b64decode(B64_CREDS).decode('utf-8'))
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Sheet Error: {e}")
        return None

# 4. Bot Commands
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to your CA Study Planner! Send me a topic or ask me to generate a study schedule.")

@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        # Gemini AI handles the thinking
        prompt = f"You are a strict but encouraging CA exam study planner. Help the student with this request: {message.text}"
        response = model.generate_content(prompt)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Oops, something went wrong: {str(e)}")

# 5. Run the Bot and Web Server Safely
if __name__ == "__main__":
    # Start the Telegram bot inside a background thread so it doesn't block Render
    bot_thread = threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True))
    bot_thread.daemon = True
    bot_thread.start()
    print("Telegram bot started in the background...")

    # Run the Flask server on the main thread so Render connects instantly
    port = int(os.environ.get("PORT", 5000))
    print(f"Web server starting on port {port}...")
    app.run(host='0.0.0.0', port=port)
