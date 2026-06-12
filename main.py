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
        "📈 TCS Tracker Running\n"
        "Breakout Level: ₹2260"
        + FOOTER
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tcs = yf.Ticker("TCS.NS")
        hist = tcs.history(period="5d")

        current_price = round(hist["Close"].iloc[-1], 2)
        day_high = round(hist["High"].iloc[-1], 2)
        day_low = round(hist["Low"].iloc[-1], 2)

        await update.message.reply_text(
            f"📊 TCS Price\n\n"
            f"Current Price: ₹{current_price}\n"
            f"Day High: ₹{day_high}\n"
            f"Day Low: ₹{day_low}"
            + FOOTER
        )

    except Exception as e:
        await update.message.reply_text(
            f"Error: {str(e)}"
            + FOOTER
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("price", price))

    app.run_polling()


if __name__ == "__main__":
    main()
