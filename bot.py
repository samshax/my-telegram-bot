import os
import sqlite3
import threading
import requests
from flask import Flask
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Render uchun Flask keep-alive
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Dr.Ali Buxgalteriya Boti Ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# API Kalitlar
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8847168101:AAGVWvBSRExuyDNgenww6dQpy4q-dOKjgD4")
GROQ_KEY = os.environ.get("GROQ_KEY", "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")

client = Groq(api_key=GROQ_KEY)

# DB ulash va jadval yaratish
def init_db():
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT, -- 'income' yoki 'expense'
            amount REAL,
            description TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def add_transaction(user_id, trans_type, amount, description):
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, ?, ?, ?)",
        (user_id, trans_type, amount, description)
    )
    conn.commit()
    conn.close()

def get_report(user_id):
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT type, amount, description FROM transactions WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "Kun davomida hech qanday kirim yoki chiqim yozilmadi."

    total_income = 0
    total_expense = 0
    details = "📊 **KUNLIK HISOBOT:**\n\n"

    for r_type, amount, desc in rows:
        if r_type == 'income':
            total_income += amount
            details += f"🟢 +{amount:,.0f} so'm ({desc})\n"
        else:
            total_expense += amount
            details += f"🔴 -{amount:,.0f} so'm ({desc})\n"

    balance = total_income - total_expense
    details += f"\n---------------------------\n"
    details += f"💰 **Jami Daromad:** {total_income:,.0f} so'm\n"
    details += f"💸 **Jami Xarajat:** {total_expense:,.0f} so'm\n"
    details += f"⚖️ **Qoldiq Balans:** {balance:,.0f} so'm"

    return details

def clear_data(user_id):
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# AI Mantiq: Matndan raqam va amalni ajratish
def process_finance_text(user_id, text):
    prompt = f"""
    Foydalanuvchi matni: "{text}"
    Sening vazifang ushbu matndan moliyaviy ma'lumotni ajratib olish.
    Javobni FAQAT quyidagi JSON formatida qaytar, ortiqcha hech narsa yozma:
    {{
        "is_finance": true/false,
        "type": "income" yoki "expense",
        "amount": raqam (masalan 50000),
        "description": "qisqa izoh",
        "is_report_request": true/false
    }}
    Agar foydalanuvchi hisobot so'rayotgan bo'lsa ("hisobot", "kun oxiri", "natija"), "is_report_request": true qil.
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    
    import json
    try:
        data = json.loads(response.choices[0].message.content.strip())
        
        if data.get("is_report_request"):
            return get_report(user_id)
            
        if data.get("is_finance") and data.get("amount"):
            t_type = data.get("type", "expense")
            amount = float(data.get("amount"))
            desc = data.get("description", "Izohsiz")
            
            add_transaction(user_id, t_type, amount, desc)
            type_str = "Daromad (Kirim) 🟢" if t_type == "income" else "Xarajat (Chiqim) 🔴"
            return f"✅ Saqlandi!\n📌 **Turi:** {type_str}\n💵 **Summa:** {amount:,.0f} so'm\n📝 **Izoh:** {desc}"
        else:
            return "Tushundim, lekin matnda aniq summa ko'rmadim. Masalan: 'Tushlikka 40000 sarfladim' yoki 'Taksi 15000' deb yozing."
    except Exception as e:
        return "Kechirasiz, ma'lumotni tahlil qilishda xatolik bo'ldi. Iltimos, qayta urinib ko'ring."

# Telegram Handlerlar
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! Men sizning shaxsiy buxgalteringiz Dr.Ali man.\n\n"
        "Siz menga matnli yoki OVOZLI xabar yuborishingiz mumkin (Masalan: 'Bugun 100 mingga benzin quydim' yoki 'Mijozdan 500 bin sum tushdi').\n\n"
        "📌 Buyruqlar:\n"
        "/hisobot - Kunlik hisobotni olish\n"
        "/tozalash - Kunlik hisoblarni nolga tushirish"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    reply = process_finance_text(user_id, text)
    await update.message.reply_text(reply, parse_mode="Markdown")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("🎙 Ovozli xabaringiz eshitilmoqda...")
    
    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)
        file_path = "voice.ogg"
        await voice_file.download_to_drive(file_path)

        with open(file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model="whisper-large-v3",
                language="uz"
            )
        
        recognized_text = transcription.text
        await update.message.reply_text(f"📝 **Eshitildi:** \"{recognized_text}\"", parse_mode="Markdown")
        
        reply = process_finance_text(user_id, recognized_text)
        await update.message.reply_text(reply, parse_mode="Markdown")

        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        print(f"Ovoz xatosi: {e}")
        await update.message.reply_text("Ovozni tanib olishda xatolik bo'ldi.")

async def handle_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    report = get_report(user_id)
    await update.message.reply_text(report, parse_mode="Markdown")

async def handle_clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_data(user_id)
    await update.message.reply_text("🧹 Barcha hisob-kitoblar tozalandi! Yangi kunni 0 dan boshlashingiz mumkin.")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hisobot", handle_report_cmd))
    app.add_handler(CommandHandler("tozalash", handle_clear_cmd))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("Dr.Ali Buxgalter boti ishga tushdi ✅")
    app.run_polling()
