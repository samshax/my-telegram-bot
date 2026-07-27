import os
import threading
from flask import Flask
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# 1. Render port xatoligini oldini olish uchun kichik web-server (Flask)
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda! 🤖"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# 2. Telegram va Groq tokenlari
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8847168101:AAGVWvBSRExuyDNgenww6dQpy4q-dOKjgD4")
GROQ_KEY = os.environ.get("GROQ_KEY", "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")

client = Groq(api_key=GROQ_KEY)

# 3. Telegram bot komandalari va muloqot mantiqi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Men Sun'iy Intellekt yordamchisiman. Savolingizni yozing 🤖")

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Sen yordamchi botsan. Foydalanuvchi qaysi tilda yozsa, shu tilda qisqa javob ber."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        await update.message.reply_text("Kechirasiz, javob tayyorlashda xatolik yuz berdi.")

# 4. Asosiy ishga tushirish qismi
if __name__ == "__main__":
    # Web serverni arqa fonda (thread) ishga tushiramiz
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Telegram botni ishga tushiramiz
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    
    print("Bot ishga tushdi ✅")
    app.run_polling()