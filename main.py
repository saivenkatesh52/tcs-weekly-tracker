from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import json
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

BREAKOUT_LEVEL = 2260
STATE_FILE = "tracker_state.json"

FOOTER = "\n\n━━━━━━━━━━━━\nCreated by Sai Venkatesh"


# -------------------------
# STATE MANAGEMENT
# -------------------------

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"alert_sent": False}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# -------------------------
# DATA FUNCTIONS
# -------------------------

def get_current_price():
    tcs = yf.Ticker("TCS.NS")
    hist = tcs.history(period="5d")

    if len(hist) == 0:
        return None

    return round(hist["Close"].iloc[-1], 2)


def get_weekly_data():
    tcs = yf.Ticker("TCS.NS")
    return tcs.history(period="6mo", interval="1wk")


def get_breakout_info():
    df = get_weekly_data()

    for idx, row in df.iterrows():
        close_price = round(row["Close"], 2)

        if close_price > BREAKOUT_LEVEL:
            return {
                "status": "✅ Breakout Done",
                "buy_price": close_price,
                "week": idx.strftime("%d-%b-%Y")
            }

    return {
        "status": "⏳ Monitoring",
        "buy_price": None,
        "week": None
    }


# -------------------------
# COMMANDS
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📈 TCS Weekly Tracker Active\n\n"
        "Commands:\n"
        "/status\n"
        "/price\n"
        "/weekly\n"
        "/signal\n"
        "/breakdown"
        + FOOTER
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_price = get_current_price()

    await update.message.reply_text(
        f"📈 TCS Tracker Running\n\n"
        f"Current Price: ₹{current_price}\n"
        f"Breakout Level: ₹{BREAKOUT_LEVEL}"
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
        )


async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        df = get_weekly_data().tail(8)

        message = "📅 Last 8 Weekly Closes\n\n"

        for idx, row in df.iterrows():
            message += (
                f"{idx.strftime('%d-%b-%Y')} : "
                f"₹{round(row['Close'], 2)}\n"
            )

        await update.message.reply_text(
            message + FOOTER
        )

    except Exception as e:
        await update.message.reply_text(
            f"Error: {str(e)}"
        )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        info = get_breakout_info()
        current_price = get_current_price()
        current_date_str = datetime.now().strftime('%d-%b-%Y %I:%M %p')

        msg = (
            f"🚦 TCS SIGNAL\n\n"
            f"Signal Date: {current_date_str}\n"
            f"Live Price: ₹{current_price}\n"
            f"Buy Price: Weekly close above ₹{BREAKOUT_LEVEL}\n\n"
        )

        if info["buy_price"] is None:
            msg += "Is Buy Price triggered? : No"
        else:
            diff_percent = round(
                ((current_price - BREAKOUT_LEVEL) / BREAKOUT_LEVEL) * 100,
                2
            )
            msg += (
                "Is Buy Price triggered? : Yes\n"
                f"Breakout done and closed above ₹{BREAKOUT_LEVEL}\n"
                f"Triggered Week: {info['week']}\n"
                f"Difference: {diff_percent}% (from ₹{BREAKOUT_LEVEL})"
            )

        await update.message.reply_text(
            msg + FOOTER
        )

    except Exception as e:
        await update.message.reply_text(
            f"Error: {str(e)}"
        )


async def breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get data for the last 2 months (~8 weeks)
        df = get_weekly_data().tail(8)

        message = (
            f"⚠ Last 2 Months - Weekly Closes Below ₹{BREAKOUT_LEVEL}\n\n"
        )

        found = False

        for idx, row in df.iterrows():

            close_price = round(row["Close"], 2)

            if close_price < BREAKOUT_LEVEL:
                found = True

                message += (
                    f"{idx.strftime('%d-%b-%Y')} : "
                    f"₹{close_price}\n"
                )

        if not found:
            message += "No breakdown candles found in the last 2 months."

        await update.message.reply_text(
            message + FOOTER
        )

    except Exception as e:
        await update.message.reply_text(
            f"Error: {str(e)}"
        )


# -------------------------
# MAIN
# -------------------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("weekly", weekly))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("breakdown", breakdown))

    app.run_polling()


if __name__ == "__main__":
    main()