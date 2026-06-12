from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import os
import yfinance as yf
import pandas as pd
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

FOOTER = "\n\n━━━━━━━━━━━━\nCreated by Sai Venkatesh"

POPULAR_STOCKS = {
    "TCS": "TCS.NS",
    "Reliance": "RELIANCE.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "SBI": "SBIN.NS",
    "ITC": "ITC.NS",
    "L&T": "LT.NS"
}

def get_company_keyboard(command, chat_id, extra_data=""):
    state = get_chat_state(chat_id)
    keyboard = []
    row = []
    
    tickers = list(state.keys())
    for name, t in POPULAR_STOCKS.items():
        if t not in tickers:
            tickers.append(t)
            
    for ticker in tickers:
        display_name = ticker.replace(".NS", "")
        callback_data = f"{command}:{ticker}"
        if extra_data:
            callback_data += f":{extra_data}"
            
        row.append(InlineKeyboardButton(display_name, callback_data=callback_data))
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    return InlineKeyboardMarkup(keyboard)


# -------------------------
# STATE MANAGEMENT (IN-MEMORY)
# -------------------------

MEMORY_STATE = {}

def get_chat_state(chat_id):
    if chat_id not in MEMORY_STATE:
        MEMORY_STATE[chat_id] = {
            "TCS.NS": {
                "breakout_level": 2260,
                "signal_date": datetime.now()
            }
        }
    return MEMORY_STATE[chat_id]

def get_breakout_level(chat_id, ticker):
    state = get_chat_state(chat_id)
    if ticker in state:
        return state[ticker]["breakout_level"]
    return None

def get_signal_date(chat_id, ticker):
    state = get_chat_state(chat_id)
    if ticker in state:
        return state[ticker]["signal_date"]
    return None

def set_breakout_level(chat_id, ticker, level):
    state = get_chat_state(chat_id)
    state[ticker] = {
        "breakout_level": level,
        "signal_date": datetime.now()
    }


# -------------------------
# DATA FUNCTIONS
# -------------------------

def get_current_price(ticker="TCS.NS"):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="5d")

    if len(hist) == 0:
        return None

    return round(hist["Close"].iloc[-1], 2)


def get_weekly_data(ticker="TCS.NS"):
    stock = yf.Ticker(ticker)
    return stock.history(period="6mo", interval="1wk")


def get_breakout_info(ticker, breakout_level, signal_date):
    df = get_weekly_data(ticker)

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
    state = get_chat_state(chat_id)

    msg = "📈 Tracker Status\n\n"
    for ticker, data in state.items():
        current_price = get_current_price(ticker)
        msg += f"🔸 **{ticker}**\nLive Price: ₹{current_price}\nBreakout Level: ₹{data['breakout_level']}\n\n"

    await update.message.reply_text(msg.strip() + FOOTER)


async def handle_price(message, ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")

        current_price = round(hist["Close"].iloc[-1], 2)
        day_high = round(hist["High"].iloc[-1], 2)
        day_low = round(hist["Low"].iloc[-1], 2)

        await message.reply_text(
            f"📊 {ticker} Price\n\n"
            f"Current Price: ₹{current_price}\n"
            f"Day High: ₹{day_high}\n"
            f"Day Low: ₹{day_low}"
            + FOOTER
        )

    except Exception as e:
        await message.reply_text(f"Error fetching data for {ticker}: {str(e)}")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        reply_markup = get_company_keyboard("price", update.message.chat_id)
        await update.message.reply_text("Choose a company:", reply_markup=reply_markup)
        return
        
    ticker = context.args[0].upper()
    if not ticker.endswith(".NS"): ticker += ".NS"
    await handle_price(update.message, ticker)


async def handle_weekly(message, ticker):
    try:
        df = get_weekly_data(ticker).tail(8)

        msg = f"📅 {ticker} Last 8 Weekly Closes\n\n"

        for idx, row in df.iterrows():
            msg += f"{idx.strftime('%d-%b-%Y')} : ₹{round(row['Close'], 2)}\n"

        await message.reply_text(msg + FOOTER)

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        reply_markup = get_company_keyboard("weekly", update.message.chat_id)
        await update.message.reply_text("Choose a company:", reply_markup=reply_markup)
        return
        
    ticker = context.args[0].upper()
    if not ticker.endswith(".NS"): ticker += ".NS"
    await handle_weekly(update.message, ticker)


async def handle_signal(message, chat_id, ticker):
    try:
        breakout_level = get_breakout_level(chat_id, ticker)
        
        if breakout_level is None:
            await message.reply_text(f"No breakout level set for {ticker}. Use /set_breakout <price> to set one." + FOOTER)
            return
            
        signal_date = get_signal_date(chat_id, ticker)
        info = get_breakout_info(ticker, breakout_level, signal_date)
        current_price = get_current_price(ticker)
        
        signal_date_str = signal_date.strftime('%d-%b-%Y %I:%M %p')

        msg = (
            f"🚦 {ticker} SIGNAL\n\n"
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

        await message.reply_text(msg + FOOTER)

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        reply_markup = get_company_keyboard("signal", update.message.chat_id)
        await update.message.reply_text("Choose a company:", reply_markup=reply_markup)
        return
        
    ticker = context.args[0].upper()
    if not ticker.endswith(".NS"): ticker += ".NS"
    await handle_signal(update.message, update.message.chat_id, ticker)


async def handle_breakdown(message, chat_id, ticker):
    try:
        breakout_level = get_breakout_level(chat_id, ticker)
        
        if breakout_level is None:
            await message.reply_text(f"No breakout level set for {ticker}." + FOOTER)
            return
            
        df = get_weekly_data(ticker).tail(8)
        msg = f"⚠ {ticker} Last 2 Months - Weekly Closes Below ₹{breakout_level}\n\n"

        found = False
        for idx, row in df.iterrows():
            close_price = round(row["Close"], 2)
            if close_price < breakout_level:
                found = True
                msg += f"{idx.strftime('%d-%b-%Y')} : ₹{close_price}\n"

        if not found:
            msg += "No breakdown candles found in the last 2 months."

        await message.reply_text(msg + FOOTER)

    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


async def breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        reply_markup = get_company_keyboard("breakdown", update.message.chat_id)
        await update.message.reply_text("Choose a company:", reply_markup=reply_markup)
        return
        
    ticker = context.args[0].upper()
    if not ticker.endswith(".NS"): ticker += ".NS"
    await handle_breakdown(update.message, update.message.chat_id, ticker)


async def set_breakout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) == 0:
            await update.message.reply_text("Please provide a price. Usage: /set_breakout 2300" + FOOTER)
            return
            
        if len(context.args) == 1:
            level = float(context.args[0])
            reply_markup = get_company_keyboard("set", update.message.chat_id, extra_data=str(level))
            await update.message.reply_text(f"Choose a company for breakout level ₹{level}:", reply_markup=reply_markup)
            return
        
        chat_id = update.message.chat_id
        ticker = context.args[0].upper()
        if not ticker.endswith(".NS"): ticker += ".NS"
        level = float(context.args[1])
        
        set_breakout_level(chat_id, ticker, level)
        await update.message.reply_text(f"✅ Breakout level for {ticker} updated to ₹{level}" + FOOTER)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number format." + FOOTER)


async def check_breakout_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    state = get_chat_state(chat_id)
    
    for ticker, data in state.items():
        breakout_level = data["breakout_level"]
        current_price = get_current_price(ticker)
        
        if current_price and current_price > breakout_level:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚨 BREAKOUT ALERT 🚨\n\n{ticker} is currently trading above ₹{breakout_level}!\nCurrent Price: ₹{current_price}" + FOOTER
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


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    command = data[0]
    ticker = data[1]
    
    chat_id = query.message.chat_id
    
    if command == "price":
        await handle_price(query.message, ticker)
    elif command == "weekly":
        await handle_weekly(query.message, ticker)
    elif command == "signal":
        await handle_signal(query.message, chat_id, ticker)
    elif command == "breakdown":
        await handle_breakdown(query.message, chat_id, ticker)
    elif command == "set":
        level = float(data[2])
        set_breakout_level(chat_id, ticker, level)
        await query.message.edit_text(f"✅ Breakout level for {ticker} updated to ₹{level}" + FOOTER)


# -------------------------
# MAIN
# -------------------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
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