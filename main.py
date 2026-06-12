from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import yfinance as yf

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

FOOTER = "\n\n━━━━━━━━━━━━\nCreated by Sai Venkatesh"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"📈 TCS Weekly Tracker Active\n\n"
"Available Commands:\n"
"/status\n"
"/price\n"
"/help"
+ FOOTER
)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"Available Commands:\n\n"
"/status - Tracker status\n"
"/price - Current TCS price\n"
"/help - Show commands"
+ FOOTER
)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"✅ TCS Tracker Running\n\n"
"Stock: NSE:TCS\n"
"Breakout Level: ₹2260\n\n"
"Status: Monitoring Weekly Close"
+ FOOTER
)

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
ticker = yf.Ticker("TCS.NS")
data = ticker.history(period="5d")

    if len(data) == 0:
        await update.message.reply_text(
            "Unable to fetch TCS price currently." + FOOTER
        )
        return

    price = round(data["Close"].iloc[-1], 2)

    await update.message.reply_text(
        f"📊 NSE:TCS\n\n"
        f"Current Price: ₹{price}"
        + FOOTER
    )

except Exception as e:
    await update.message.reply_text(
        f"Error fetching price:\n{str(e)}"
        + FOOTER
    )

def main():
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("price", price))

print("TCS Tracker Bot Started")

app.run_polling()

if name == "main":
main()
