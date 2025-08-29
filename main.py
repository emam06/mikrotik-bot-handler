from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "6725359383:AAGgYzqpuq7-b7Miv-_Y4NZgkhhoybBJJWM"
CLOUD_RUN_URL = "https://mikrotik-bot-handler-234478907955.europe-west1.run.app"

app = Flask(__name__)
bot_app = ApplicationBuilder().token(TOKEN).build()

# ====== Example command ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت شغال على Cloud Run باستخدام Webhook!")

bot_app.add_handler(CommandHandler("start", start))

# ====== Webhook endpoint ======
@app.route(f"/{TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put(update)
    return "ok"

# ====== Main ======
if __name__ == "__main__":
    bot_app.initialize()
    
    # ضبط Webhook على رابط Cloud Run + Token
    webhook_url = f"{CLOUD_RUN_URL}/{TOKEN}"
    bot_app.bot.set_webhook(webhook_url)
    
    # تشغيل Flask على PORT المتاح
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
