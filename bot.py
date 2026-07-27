import os
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Tokenlarni o'zgaruvchiga olamiz
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8847168101:AAGVWvBSRExuyDNgenww6dQpy4q-dOKjgD4")
GROQ_KEY = os.environ.get("GROQ_KEY", "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")

# Groq mijozini to'g'ri ishga tushirish
client = Groq(api_key=GROQ_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Savolingizni yozing 🤖")

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

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
    
    print("Bot ishga tushdi ✅")
    app.run_polling()
