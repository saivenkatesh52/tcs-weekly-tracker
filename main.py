from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import json
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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


def get_breakout_level():
    state = load_state()
    return state.get("breakout_level", 2260)


def set_breakout_level(level):
    state = load_state()
    state["breakout_level"] = level
    save_state(state)


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
    breakout_level = get_breakout_level()

    for idx, row in df.iloc[::-1].iterrows():
        close_price = round(row["Close"], 2)

        if close_price > breakout_level:
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
        "/breakdown\n"
        "/set_breakout <price>"
        + FOOTER
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_price = get_current_price()
    breakout_level = get_breakout_level()

    await update.message.reply_text(
        f"📈 TCS Tracker Running\n\n"
        f"Current Price: ₹{current_price}\n"
        f"Breakout Level: ₹{breakout_level}"
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
        breakout_level = get_breakout_level()

        msg = (
            f"🚦 TCS SIGNAL\n\n"
            f"Signal Date: {current_date_str}\n"
            f"Live Price: ₹{current_price}\n"
            f"Buy Price: Weekly close above ₹{breakout_level}\n\n"
        )

        if info["buy_price"] is None:
            msg += "Is Buy Price triggered? : No"
        else:
            diff_percent = round(
                ((current_price - breakout_level) / breakout_level) * 100,
                2
            )
            msg += (
                "Is Buy Price triggered? : Yes\n"
                f"Breakout done and closed above ₹{breakout_level}\n"
                f"Triggered Week: {info['week']}\n"
                f"Difference: {diff_percent}% (from ₹{breakout_level})"
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
        breakout_level = get_breakout_level()

        message = (
            f"⚠ Last 2 Months - Weekly Closes Below ₹{breakout_level}\n\n"
        )

        found = False

        for idx, row in df.iterrows():

            close_price = round(row["Close"], 2)

            if close_price < breakout_level:
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


async def set_breakout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Please provide a price. Usage: /set_breakout 2300" + FOOTER)
            return
        
        level = float(context.args[0])
        set_breakout_level(level)
        await update.message.reply_text(f"✅ Breakout level updated to ₹{level}" + FOOTER)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number format." + FOOTER)


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
    app.add_handler(CommandHandler("set_breakout", set_breakout))

    app.run_polling()


if __name__ == "__main__":
    main()