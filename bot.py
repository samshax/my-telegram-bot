import os
import json
import sqlite3
import asyncio
import threading
from datetime import datetime
from flask import Flask
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# Render uchun Flask keep-alive
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Dr.Ali Buxgalteriya Boti 24/7 Ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# API Kalitlar
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8847168101:AAGVWvBSRExuyDNgenww6dQpy4q-dOKjgD4")
GROQ_KEY = os.environ.get("GROQ_KEY", "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")

client = Groq(api_key=GROQ_KEY)

# DB ulash
def init_db():
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            description TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def add_transaction(user_id, trans_type, amount, description):
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO transactions (user_id, type, amount, description, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, trans_type, amount, description, now_str)
    )
    conn.commit()
    conn.close()

def get_report_by_period(user_id, period="month"):
    conn = sqlite3.connect("finance.db")
    cursor = conn.cursor()
    
    if period == "today":
        filter_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT type, amount, description, date FROM transactions WHERE user_id = ? AND date LIKE ?", (user_id, f"{filter_date}%"))
        title = "📅 **BUGUNGI HISOBOT:**"
    elif period == "month":
        filter_date = datetime.now().strftime("%Y-%m")
        cursor.execute("SELECT type, amount, description, date FROM transactions WHERE user_id = ? AND date LIKE ?", (user_id, f"{filter_date}%"))
        title = "🗓 **SHU OYLIK (30 KUNLIK) HISOBOT:**"
    else:  # all_time
        cursor.execute("SELECT type, amount, description, date FROM transactions WHERE user_id = ?", (user_id,))
        title = "📊 **UMUMIY (BARCHA VAQT BO'YICHA) HISOBOT:**"

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return f"{title}\n\nUshbu davr bo'yicha hech qanday ma'lumot topilmadi."

    total_income = 0
    total_expense = 0
    
    for r_type, amount, desc, t_date in rows:
        if r_type == 'income':
            total_income += amount
        else:
            total_expense += amount

    balance = total_income - total_expense
    
    report = f"{title}\n\n"
    report += f"🟢 **Jami Tushum (Foyda/Kirim):** {total_income:,.0f} so'm\n"
    report += f"🔴 **Jami Xarajat (Chiqim):** {total_expense:,.0f} so'm\n"
    report += f"---------------------------\n"
    report += f"⚖️ **Sof Qoldiq (Balans):** {balance:,.0f} so'm\n"
    report += f"📝 **Operatsiyalar soni:** {len(rows)} ta"

    return report

def process_finance_text(user_id, text):
    prompt = f"""
    Foydalanuvchi matni: "{text}"
    Sening vazifang matndan moliyaviy ma'lumotni yoki hisobot so'rovini aniqlash.
    Javobni FAQAT quyidagi JSON formatida qaytar:
    {{
        "is_report_request": true/false,
        "period": "today" yoki "month" yoki "all",
        "is_finance": true/false,
        "type": "income" yoki "expense",
        "amount": raqam,
        "description": "qisqa izoh"
    }}
    Mantiq:
    - Agar hisobot, foyda, xarajat, oylik natija so'ralgan bo'lsa: "is_report_request": true. Period belgilash: oy/bir oy desa "month", bugun desa "today", hammasi/jami desa "all".
    - Agar pul kirdi/chiqdi/sarflandi aytilgan bo'lsa: "is_finance": true, type "income" (daromad) yoki "expense" (xarajat).
    """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    
    try:
        data = json.loads(response.choices[0].message.content.strip())
        
        if data.get("is_report_request"):
            period = data.get("period", "month")
            return get_report_by_period(user_id, period)
            
        if data.get("is_finance") and data.get("amount"):
            t_type = data.get("type", "expense")
            amount = float(data.get("amount"))
            desc = data.get("description", "Izohsiz")
            
            add_transaction(user_id, t_type, amount, desc)
            type_str = "Daromad (Kirim) 🟢" if t_type == "income" else "Xarajat (Chiqim) 🔴"
            return f"✅ Saqlandi!\n📌 **Turi:** {type_str}\n💵 **Summa:** {amount:,.0f} so'm\n📝 **Izoh:** {desc}\n\n*(Barcha ma'lumotlar xotirada doimiy saqlanadi)*"
        else:
            return "Tushundim. Moliyaviy kirim-chiqim yozing (masalan: 'Tushlik 40000') yoki hisobot so'rang (masalan: 'Shu oylik xarajatlarim')."
    except Exception as e:
        return "Xatolik yuz berdi, qaytadan urinib ko'ring."

# Telegram Handlerlar
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! Men Dr.Ali — sizning doimiy shaxsiy buxgalteringizman.\n\n"
        "Men barcha xarajat va foydalaringizni **hech qachon o'chirmasdan** xotirada saqlab boraman.\n\n"
        "💡 **Menga qanday yozishingiz mumkin:**\n"
        "• 'Bugun benzinga 120 ming berdim'\n"
        "• 'Mijozdan 2 mln tushdi'\n"
        "• 'Shu oylik hisobotni ber'\n"
        "• 'Bir oydan beri qancha foyda qildim?'\n"
        "• Ovozli xabar (voice) yuborishingiz ham mumkin!"
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
        await update.message.reply_text("Ovozni tanib olishda xatolik bo'ldi.")

async def report_month_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    report = get_report_by_period(user_id, "month")
    await update.message.reply_text(report, parse_mode="Markdown")

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("hisobot", report_month_cmd))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    print("Dr.Ali Buxgalter boti ishga tushdi ✅")
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        # Doimiy ishlashni ta'minlash
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
