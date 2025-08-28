import logging
import random
import string
from datetime import datetime
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from routeros_api import RouterOsApiPool

# إعدادات MikroTik
MIKROTIK_IP = '172.75.88.129'
MIKROTIK_USER = 'admin'
MIKROTIK_PASSWORD = '3071985'
API_PORT = 8728

# إعدادات البوت
TOKEN = "6725359383:AAGgYzqpuq7-b7Miv-_Y4NZgkhhoybBJJWM"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

def generate_username(length=8):
    return ''.join(random.choices(string.digits, k=length))

def create_mikrotik_user(username, data_limit, time_limit):
    try:
        connection = RouterOsApiPool(
            host=MIKROTIK_IP,
            username=MIKROTIK_USER,
            password=MIKROTIK_PASSWORD,
            port=API_PORT,
            plaintext_login=True
        )
        api = connection.get_api()
        profile = "3M"
        creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # صححنا هنا

        api.get_resource('/ip/hotspot/user').add(
            name=username,
            profile=profile,
            limit_bytes_total=str(data_limit),
            limit_uptime=str(time_limit),
            comment=f"autoRemove start: {creation_time}"
        )
        connection.disconnect()
        return True
    except Exception as e:
        logger.error(f"❌ خطأ: {e}")
        return False

async def new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 5 جنيه - 500MB / ساعتين", callback_data="plan_5")],
        [InlineKeyboardButton("💰 10 جنيه - 1300MB / 24 ساعة", callback_data="plan_10")],
        [InlineKeyboardButton("🛠️ تخصيص باقة", callback_data="custom_plan")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 اختر الباقة:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "plan_5":
        data_limit = 500 * 1024 * 1024
        time_limit = "2h"
    elif data == "plan_10":
        data_limit = 1300 * 1024 * 1024
        time_limit = "1d"
    else:
        data_limit = None

    if data_limit:
        username = generate_username()
        if create_mikrotik_user(username, data_limit, time_limit):
            response = f"✅ تم إنشاء المستخدم\n👤 {username}\n📶 {data_limit // (1024*1024)}MB\n🕒 {time_limit}"
        else:
            response = "❌ فشل في إنشاء المستخدم."
        await query.message.reply_text(response)

async def manual_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ تخصيص الباقة لسه تحت التطوير.")

# Telegram
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("newuser", new_user))
application.add_handler(CallbackQueryHandler(button_handler))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manual_entry_handler))

# Flask routes
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK", 200

@flask_app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
