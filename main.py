from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import yfinance as yf
import pandas as pd
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

FOOTER = "\n\n━━━━━━━━━━━━\nCreated by Sai Venkatesh"


# -------------------------
# STATE MANAGEMENT (IN-MEMORY)
# -------------------------

MEMORY_STATE = {}

def get_chat_state(chat_id):
    if chat_id not in MEMORY_STATE:
        MEMORY_STATE[chat_id] = {
            "breakout_level": 2260,
            "signal_date": datetime.now()
        }
    return MEMORY_STATE[chat_id]

def get_breakout_level(chat_id):
    return get_chat_state(chat_id)["breakout_level"]

def get_signal_date(chat_id):
    return get_chat_state(chat_id)["signal_date"]

def set_breakout_level(chat_id, level):
    state = get_chat_state(chat_id)
    state["breakout_level"] = level
    state["signal_date"] = datetime.now()


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


def get_breakout_info(breakout_level, signal_date):
    df = get_weekly_data()

    for idx, row in df.iloc[::-1].iterrows():
        candle_date = idx.tz_localize(None) if idx.tzinfo else idx
        
        # Check if the candle ends AFTER the signal date
        if candle_date + pd.Timedelta(days=7) >= signal_date:
            close_price = round(row["Close"], 2)

            if close_price > breakout_level:
                return {
                    "status": "✅ Breakout Done",
                    "buy_price": close_price,
                    "week": idx.strftime("%d-%b-%Y")
                }
        else:
            # We have reached candles older than the signal date
            break

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
        "/set_breakout <price>\n"
        "/monitor\n"
        "/stop_monitor"
        + FOOTER
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    current_price = get_current_price()
    breakout_level = get_breakout_level(chat_id)

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
        chat_id = update.message.chat_id
        breakout_level = get_breakout_level(chat_id)
        signal_date = get_signal_date(chat_id)
        info = get_breakout_info(breakout_level, signal_date)
        current_price = get_current_price()
        
        signal_date_str = signal_date.strftime('%d-%b-%Y %I:%M %p')

        msg = (
            f"🚦 TCS SIGNAL\n\n"
            f"Signal Date: {signal_date_str}\n"
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
        chat_id = update.message.chat_id
        # Get data for the last 2 months (~8 weeks)
        df = get_weekly_data().tail(8)
        breakout_level = get_breakout_level(chat_id)

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
        
        chat_id = update.message.chat_id
        level = float(context.args[0])
        set_breakout_level(chat_id, level)
        await update.message.reply_text(f"✅ Breakout level updated to ₹{level}" + FOOTER)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number format." + FOOTER)


async def check_breakout_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    breakout_level = get_breakout_level(chat_id)
    
    current_price = get_current_price()
    if current_price and current_price > breakout_level:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚨 BREAKOUT ALERT 🚨\n\nTCS is currently trading above ₹{breakout_level}!\nCurrent Price: ₹{current_price}" + FOOTER
        )


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    
    # Remove existing jobs
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
        
    # Run every 6 hours (21600 seconds)
    context.job_queue.run_repeating(check_breakout_job, interval=21600, first=10, chat_id=chat_id, name=str(chat_id))
    
    await update.message.reply_text("✅ Background monitoring started! I will check every 6 hours and notify you if a breakout occurs." + FOOTER)


async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
    
    await update.message.reply_text("⏹️ Background monitoring stopped." + FOOTER)


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
    app.add_handler(CommandHandler("monitor", monitor))
    app.add_handler(CommandHandler("stop_monitor", stop_monitor))

    app.run_polling()


if __name__ == "__main__":
    main()