from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8847168101:AAGVWvBSRExuyDNgenww6dQpy4q-dOKjgD4"
GROQ_KEY = "BU_YERGA_GROQ_KEYNI_YOZING"

client = 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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Savolingizni yozing 🤖")

async def ai_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Sen yordamchi botsan. Foydalanuvchi qaysi tilda yozsa, shu tilda qisqa javob ber."},
            {"role": "user", "content": user_message}
        ]
    )
    await update.message.reply_text(response.choices[0].message.content)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_reply))
print("Bot ishga tushdi ✅")
app.run_polling()
