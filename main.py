import logging
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters
from routeros_api import RouterOsApiPool
from routeros_api.exceptions import RouterOsApiConnectionError

# ✅ إعدادات MikroTik
MIKROTIK_IP = '192.168.1.11'
MIKROTIK_USER = 'admin'
MIKROTIK_PASSWORD = '3071985'
API_PORT = 8728  # تأكد من أن هذا المنفذ يعمل

# ✅ إعدادات البوت
TOKEN = "6725359383:AAGgYzqpuq7-b7Miv-_Y4NZgkhhoybBJJWM"

# ✅ تمكين التسجيل لمراقبة الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)


# ✅ إنشاء اسم مستخدم عشوائي من 3 إلى 9 أرقام
def generate_username(length=8):
    return ''.join(random.choices(string.digits, k=length))


# ✅ إنشاء مستخدم جديد في MikroTik مع تعليق بتاريخ ووقت الإنشاء
def create_mikrotik_user(username, data_limit, time_limit):
    try:
        connection = RouterOsApiPool(host=MIKROTIK_IP,
                                     username=MIKROTIK_USER,
                                     password=MIKROTIK_PASSWORD,
                                     port=API_PORT,
                                     plaintext_login=True)
        api = connection.get_api()

        profile = "3M"

        # ✅ الحصول على الوقت الحالي بصيغة واضحة
        creation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ✅ تحويل القيم إلى نص (`str`) لتجنب الأخطاء
        data_limit = str(data_limit)
        time_limit = str(time_limit)

        # 🔹 إضافة المستخدم مع تحديد الحد الأقصى للبيانات والوقت وإضافة التعليق
        api.get_resource('/ip/hotspot/user').add(
            name=username,
            profile=profile,
            limit_bytes_total=data_limit,
            limit_uptime=time_limit,
            comment=f"autoRemove start: {creation_time}")

        connection.disconnect()
        return True
    except RouterOsApiConnectionError as e:
        logger.error(f"❌ خطأ في الاتصال بـ MikroTik: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")
        return False


# ✅ أمر /newuser لإضافة مستخدم جديد
async def new_user(update: Update, context: CallbackContext):
    keyboard = [[
        InlineKeyboardButton("💰 5 جنيه - 500MB / ساعتين",
                             callback_data="plan_5")
    ],
                [
                    InlineKeyboardButton("💰 10 جنيه - 1300MB / 24 ساعة",
                                         callback_data="plan_10")
                ],
                [
                    InlineKeyboardButton("🛠️ تخصيص باقة",
                                         callback_data="custom_plan")
                ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📌 اختر الباقة المناسبة لك أو اضغط على *تخصيص باقة* لإدخال القيم يدويًا:",
        reply_markup=reply_markup)


# ✅ التعامل مع اختيار المستخدم للباقة
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    data = query.data

    # ✅ التعامل مع الباقات الثابتة
    if data == "plan_5":
        data_limit = 500 * 1024 * 1024  # 500MB
        time_limit = "2h"
    elif data == "plan_10":
        data_limit = 1300 * 1024 * 1024  # 1300MB
        time_limit = "1d"
    else:
        data_limit = None

    if data_limit:
        username = generate_username()
        if create_mikrotik_user(username, data_limit, time_limit):
            response = (f"✅ *تم إنشاء المستخدم بنجاح!*\n\n"
                        f"📶 *سعة التحميل:* {data_limit // (1024 * 1024)}MB\n"
                        f"🕒 *الوقت:* {time_limit}\n\n"
                        f"👤 *اسم المستخدم:* `{username}`\n\n"
                        "يمكنك استخدام هذه البيانات للاتصال بالشبكة.")
        else:
            response = "❌ فشل في إنشاء المستخدم. يرجى المحاولة لاحقًا."

        await query.message.reply_text(response, parse_mode="Markdown")
        return

    # ✅ التعامل مع "تخصيص باقة"
    if data == "custom_plan":
        await query.message.reply_text(
            "✏️ أرسل الآن اسم المستخدم (من 3 إلى 9 أرقام):")
        context.user_data["waiting_for_username"] = True
        return

    # ✅ التعامل مع اختيار وحدة القياس (MB أو GB)
    if data.startswith("custom_unit_"):
        unit = data.split("_")[-1]
        context.user_data["unit"] = unit  # حفظ وحدة القياس المختارة
        context.user_data[
            "waiting_for_quota"] = True  # الانتقال للخطوة التالية
        await query.message.reply_text(
            f"✏️ أرسل الآن سعة التحميل ({unit}) (مثال: `1000`).")
        return


# ✅ التعامل مع الإدخال اليدوي
async def manual_entry_handler(update: Update, context: CallbackContext):
    message = update.message.text.strip()

    # ✅ استقبال اسم المستخدم المخصص
    if "waiting_for_username" in context.user_data:
        if message.isdigit() and 3 <= len(message) <= 9:
            context.user_data["custom_username"] = message
            context.user_data.pop("waiting_for_username")

            keyboard = [[
                InlineKeyboardButton("MB", callback_data="custom_unit_MB"),
                InlineKeyboardButton("GB", callback_data="custom_unit_GB")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🔹 اختر وحدة القياس:",
                                            reply_markup=reply_markup)
        else:
            await update.message.reply_text(
                "⚠️ يرجى إدخال اسم مستخدم يحتوي على أرقام فقط (من 3 إلى 9 أرقام)."
            )
        return

    # ✅ استقبال سعة التحميل بعد اختيار الوحدة
    if "waiting_for_quota" in context.user_data:
        try:
            quota = int(message)
            unit = context.user_data.get("unit", "MB")  # جلب الوحدة المختارة

            if unit == "GB":
                data_limit = quota * 1024 * 1024 * 1024
            else:
                data_limit = quota * 1024 * 1024

            context.user_data["data_limit"] = data_limit
            context.user_data.pop("waiting_for_quota")  # إزالة حالة الانتظار

            await update.message.reply_text(
                "🕒 الآن، أرسل عدد الأيام (مثال: `3`).")
            context.user_data["waiting_for_days"] = True
        except ValueError:
            await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح.")
        return

    # ✅ استقبال عدد الأيام وإتمام العملية
    if "waiting_for_days" in context.user_data:
        try:
            days = int(message)
            time_limit = f"{days}d"
            data_limit = context.user_data["data_limit"]
            username = context.user_data["custom_username"]

            success = create_mikrotik_user(username, data_limit, time_limit)

            if success:
                response = (
                    f"✅ *تم إنشاء المستخدم بنجاح!*\n\n"
                    f"📶 *سعة التحميل:* {data_limit // (1024 * 1024)}MB\n"
                    f"🕒 *الوقت:* {time_limit}\n\n"
                    f"👤 *اسم المستخدم:* `{username}`\n\n"
                    "يمكنك استخدام هذه البيانات للاتصال بالشبكة.")
                await update.message.reply_text(response,
                                                parse_mode="Markdown")
            else:
                await update.message.reply_text(
                    "❌ فشل في إنشاء المستخدم. يرجى المحاولة لاحقًا.")

            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("⚠️ يرجى إدخال رقم صحيح للأيام.")
        return


# ✅ تشغيل البوت
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("newuser", new_user))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, manual_entry_handler))
    app.run_polling()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)
