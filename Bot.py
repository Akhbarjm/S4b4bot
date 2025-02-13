 import os
import json
import sqlite3
import logging
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from googletrans import Translator

# تنظیمات اولیه
TOKEN = "7597835014:AAFOTbE1FlM7JMg6cWFQ2mW9IAY2CkupO7Y"  # توکن ربات
WEBHOOK_URL = "https://s4b4bot.onrender.com/webhook"  # آدرس وبهوک
ADMIN_IDS = ["pelakbg"]  # آیدی ادمین‌های اصلی
DB_FILE = "bot_database.db"  # نام فایل دیتابیس

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
translator = Translator()

# تنظیمات لاگ‌گیری
logging.basicConfig(level=logging.INFO)

# ---------------------- ایجاد و مدیریت دیتابیس ---------------------- #
def init_db():
    """ساخت دیتابیس و جداول لازم در صورت عدم وجود"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        role TEXT CHECK(role IN ('admin', 'superadmin', 'masteradmin'))
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        channel_id TEXT UNIQUE,
        filter_white TEXT,
        filter_black TEXT,
        send_to TEXT,
        FOREIGN KEY (admin_id) REFERENCES admins(user_id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS translations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_text TEXT,
        translated_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()

# ---------------------- هندل کردن پیام‌ها ---------------------- #
@bot.message_handler(commands=['start'])
def start(message):
    """پیام خوش‌آمدگویی و نمایش دستورات"""
    bot.send_message(message.chat.id, "👋 خوش آمدید! از طریق منو، امکانات ربات را بررسی کنید.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    """دریافت پیام‌های متنی و ارسال ترجمه"""
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels WHERE admin_id=?", (user_id,))
    channels = cursor.fetchall()
    conn.close()

    # هر ادمین می‌تواند لیست کانال‌های خود را دریافت کند
    for channel in channels:
        original_text = message.text
        white_filter = channel[3]
        black_filter = channel[4]
        send_to = channel[5]

        # بررسی فیلتر سفید و سیاه
        if white_filter and any(word in original_text for word in white_filter.split(',')):
            translated_text = translator.translate(original_text, dest='fa').text
            bot.send_message(send_to, f"📄 **متن ترجمه‌شده:**\n\n{translated_text}", parse_mode="Markdown")
        elif black_filter and any(word in original_text for word in black_filter.split(',')):
            continue  # پیام شامل کلمات سیاه است و ارسال نمی‌شود
        else:
            translated_text = translator.translate(original_text, dest='fa').text
            bot.send_message(send_to, f"📄 **متن ترجمه‌شده:**\n\n{translated_text}", parse_mode="Markdown")

        # اگر پیام بیش از 200 کاراکتر داشت، دکمه‌ها نمایان می‌شوند
        if len(original_text) > 200:
            markup = InlineKeyboardMarkup()
            markup.row_width = 2
            markup.add(
                InlineKeyboardButton("🆓 ترجمه گوگل", callback_data=f"google_{original_text}"),
                InlineKeyboardButton("🔍 ترجمه مشابه", callback_data=f"similar_{original_text}"),
                InlineKeyboardButton("🤖 ترجمه تخصصی", callback_data=f"ai_{original_text}")
            )
            bot.send_message(send_to, f"📄 **متن ترجمه‌شده:**\n\n{translated_text}", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """مدیریت انتخاب نوع ترجمه"""
    data = call.data.split("_", 1)
    action = data[0]
    original_text = data[1]

    if action == "google":
        translated_text = translator.translate(original_text, dest='fa').text
        bot.send_message(call.message.chat.id, f"🆓 **ترجمه گوگل:**\n\n{translated_text}", parse_mode="Markdown")

    elif action == "similar":
        bot.send_message(call.message.chat.id, "🔍 بررسی ترجمه‌های مشابه در دسترس نیست.")

    elif action == "ai":
        bot.send_message(call.message.chat.id, "🤖 ترجمه تخصصی با OpenAI به‌زودی اضافه می‌شود.")

# ---------------------- مدیریت ادمین‌ها و کانال‌ها ---------------------- #
@bot.message_handler(commands=['add_channel'])
def add_channel(message):
    """افزودن کانال به لیست ادمین"""
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ شما اجازه دسترسی ندارید.")
        return

    bot.send_message(message.chat.id, "📌 آیدی کانال موردنظر را ارسال کنید.")
    # اینجا می‌تونی کانال جدید رو به لیست اضافه کنی

@bot.message_handler(commands=['set_filters'])
def set_filters(message):
    """تنظیم فیلترهای سفید و سیاه برای کانال"""
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels WHERE admin_id=?", (user_id,))
    channels = cursor.fetchall()
    conn.close()

    for channel in channels:
        # تنظیم فیلتر سیاه و سفید برای کانال
        bot.send_message(message.chat.id, f"📌 فیلترهای سفید و سیاه برای کانال {channel[2]} را تنظیم کنید.")

# ---------------------- تنظیمات وبهوک ---------------------- #
@app.route('/webhook', methods=['POST'])
def webhook():
    """دریافت آپدیت‌های تلگرام از طریق وبهوک"""
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route('/')
def index():
    """صفحه اصلی سرور (برای بررسی وضعیت)"""
    return "ربات در حال اجرا است.", 200

# ---------------------- راه‌اندازی ربات ---------------------- #
if __name__ == "__main__":
    init_db()  # ساخت دیتابیس در صورت نیاز
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)
