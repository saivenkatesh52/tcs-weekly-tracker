from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"TCS Tracker Active\n\nCreated by Sai Venkatesh"
)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"TCS Tracker Running\nBreakout Level: ₹2260\n\nCreated by Sai Venkatesh"
)

def main():
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))

app.run_polling()

if name == "main":
main()
