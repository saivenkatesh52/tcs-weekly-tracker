from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import yfinance as yf

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

FOOTER = "\n\n━━━━━━━━━━━━\nCreated by Sai Venkatesh"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"📈 TCS Weekly Tracker Active\n\n"
"Commands:\n"
"/start\n"
"/status\n"
"/price"
+ FOOTER
)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"📈 TCS Weekly Tracker\n\n"
"Stock: NSE:TCS\n"
"Breakout Level: ₹2260\n"
"Status: Monitoring"
+ FOOTER
)

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
tcs = yf.Ticker("TCS.NS")

    info = tcs.info

    current_price = info.get("currentPrice", "N/A")
    day_high = info.get("dayHigh", "N/A")
    day_low = info.get("dayLow", "N/A")
    high_52 = info.get("fiftyTwoWeekHigh", "N/A")
    low_52 = info.get("fiftyTwoWeekLow", "N/A")

    await update.message.reply_text(
        f"📊 NSE:TCS\n\n"
        f"Current Price: ₹{current_price}\n"
        f"Day High: ₹{day_high}\n"
        f"Day Low: ₹{day_low}\n\n"
        f"52W High: ₹{high_52}\n"
        f"52W Low: ₹{low_52}"
        + FOOTER
    )

except Exception as e:
    await update.message.reply_text(
        f"Error fetching data:\n{str(e)}"
        + FOOTER
    )

def main():
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("price", price))

app.run_polling()

if name == "main":
main()
