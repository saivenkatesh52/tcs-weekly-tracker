from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import os
import yfinance as yf
import pandas as pd
import difflib
import json
from datetime import datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
IST = ZoneInfo("Asia/Kolkata")
TIMEFRAMES = ("weekly", "daily", "monthly")
MONITOR_TIMES = ("1500", "1540")

TIMEFRAME_CONFIG = {
    "weekly": {
        "label": "Weekly",
        "display_count": 8,
        "period": "2y",
        "interval": "1wk",
        "candle_days": 7,
    },
    "daily": {
        "label": "Daily",
        "display_count": 7,
        "period": "6mo",
        "interval": "1d",
        "candle_days": 1,
    },
    "monthly": {
        "label": "Monthly",
        "display_count": 6,
        "period": "5y",
        "interval": "1mo",
        "candle_days": 31,
    },
}

STOCKS_DB = {}
if os.path.exists("stocks.json"):
    with open("stocks.json", "r") as f:
        STOCKS_DB = json.load(f)


def ticker_has_data(symbol):
    try:
        hist = yf.Ticker(symbol).history(period="5d")
        return not hist.empty
    except Exception:
        return False

def find_stock_ticker(user_input):
    raw_input = user_input.strip()
    if not raw_input:
        return raw_input

    normalized = raw_input.upper()

    if normalized in STOCKS_DB.values():
        return normalized
    if raw_input in STOCKS_DB:
        return STOCKS_DB[raw_input]
    if normalized in STOCKS_DB:
        return STOCKS_DB[normalized]

    if ticker_has_data(raw_input):
        return raw_input
    if normalized != raw_input and ticker_has_data(normalized):
        return normalized

    company_names = list(STOCKS_DB.keys())
    matches = difflib.get_close_matches(normalized, company_names, n=1, cutoff=0.5)
    if matches:
        return STOCKS_DB[matches[0]]

    return normalized

FOOTER = "\n\n━━━━━━━━━━━━\nCreated by Sai Venkatesh"


# -------------------------
# STATE MANAGEMENT (IN-MEMORY)
# -------------------------

MEMORY_STATE = {}
PENDING_ACTIONS = {}

def get_chat_state(chat_id):
    if chat_id not in MEMORY_STATE:
        MEMORY_STATE[chat_id] = {timeframe: {} for timeframe in TIMEFRAMES}
    return MEMORY_STATE[chat_id]

def get_timeframe_state(chat_id, timeframe):
    state = get_chat_state(chat_id)
    if timeframe not in state:
        state[timeframe] = {}
    return state[timeframe]


def get_breakout_level(chat_id, timeframe, ticker):
    state = get_timeframe_state(chat_id, timeframe)
    if ticker in state:
        return state[ticker]["breakout_level"]
    return None


def get_signal_date(chat_id, timeframe, ticker):
    state = get_timeframe_state(chat_id, timeframe)
    if ticker in state:
        return state[ticker]["signal_date"]
    return None

def set_breakout_level(chat_id, timeframe, ticker, level):
    state = get_timeframe_state(chat_id, timeframe)
    state[ticker] = {
        "breakout_level": level,
        "signal_date": datetime.now(IST),
        "last_alert_date": None,
    }


def get_last_alert_date(chat_id, timeframe, ticker):
    state = get_timeframe_state(chat_id, timeframe)
    if ticker in state:
        return state[ticker].get("last_alert_date")
    return None


def set_last_alert_date(chat_id, timeframe, ticker, alert_date):
    state = get_timeframe_state(chat_id, timeframe)
    if ticker in state:
        state[ticker]["last_alert_date"] = alert_date


def set_pending_action(chat_id, action):
    PENDING_ACTIONS[chat_id] = action


def get_pending_action(chat_id):
    return PENDING_ACTIONS.get(chat_id)


def clear_pending_action(chat_id):
    PENDING_ACTIONS.pop(chat_id, None)


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
    return stock.history(period=TIMEFRAME_CONFIG["weekly"]["period"], interval=TIMEFRAME_CONFIG["weekly"]["interval"])


def get_daily_data(ticker="TCS.NS"):
    stock = yf.Ticker(ticker)
    return stock.history(period=TIMEFRAME_CONFIG["daily"]["period"], interval=TIMEFRAME_CONFIG["daily"]["interval"])


def get_monthly_data(ticker="TCS.NS"):
    stock = yf.Ticker(ticker)
    return stock.history(period=TIMEFRAME_CONFIG["monthly"]["period"], interval=TIMEFRAME_CONFIG["monthly"]["interval"])


def get_timeframe_data(ticker, timeframe):
    if timeframe == "weekly":
        return get_weekly_data(ticker)
    if timeframe == "daily":
        return get_daily_data(ticker)
    if timeframe == "monthly":
        return get_monthly_data(ticker)
    raise ValueError(f"Unsupported timeframe: {timeframe}")


def is_last_business_day_of_week(now_ist):
    return now_ist.weekday() == 4


def is_last_business_day_of_month(now_ist):
    import calendar

    last_day = calendar.monthrange(now_ist.year, now_ist.month)[1]
    day = datetime(now_ist.year, now_ist.month, last_day, tzinfo=IST)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return now_ist.date() == day.date()


def should_run_monitor(timeframe, now_ist):
    if timeframe == "daily":
        return True
    if timeframe == "weekly":
        return is_last_business_day_of_week(now_ist)
    if timeframe == "monthly":
        return is_last_business_day_of_month(now_ist)
    return False


def get_breakout_info(ticker, timeframe, breakout_level, signal_date):
    df = get_timeframe_data(ticker, timeframe)
    candle_days = TIMEFRAME_CONFIG[timeframe]["candle_days"]
    signal_date_naive = signal_date.astimezone(IST).replace(tzinfo=None) if signal_date.tzinfo else signal_date

    for idx, row in df.iloc[::-1].iterrows():
        candle_date = idx.tz_localize(None) if idx.tzinfo else idx
        
        if candle_date + pd.Timedelta(days=candle_days) >= signal_date_naive:
            close_price = round(row["Close"], 2)

            if close_price > breakout_level:
                return {
                    "status": "✅ Breakout Done",
                    "buy_price": close_price,
                    "candle_date": idx.strftime("%d-%b-%Y")
                }
        else:
            break

    return {
        "status": "⏳ Monitoring",
        "buy_price": None,
        "candle_date": None
    }


def get_target_timeframe_from_action(action):
    if action in TIMEFRAMES:
        return action
    if action in {"signal", "breakdown", "set", "monitor", "stop_monitor"}:
        return "weekly"
    return None


def get_target_timeframe_from_command(command):
    if command.endswith("_weekly"):
        return "weekly"
    if command.endswith("_daily"):
        return "daily"
    if command.endswith("_monthly"):
        return "monthly"
    if command.startswith("remove_"):
        if command.endswith("weekly"):
            return "weekly"
        if command.endswith("daily"):
            return "daily"
        if command.endswith("monthly"):
            return "monthly"
    if command in {"signal", "breakdown", "set", "monitor", "stop_monitor", "weekly"}:
        return "weekly"
    if command in {"daily", "monthly"}:
        return command
    return None


# -------------------------
# COMMANDS
# -------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the **Stock Tracker**!\n\n"
        "I can help you monitor breakout levels for any Yahoo Finance ticker and alert you automatically. Here are the commands you can use:\n\n"
        "🛠 **Setup & Manage**\n"
        "🔹 /set_breakout - Set a new breakout level (weekly default)\n"
        "🔹 /set_breakout_daily - Set a daily breakout level\n"
        "🔹 /set_breakout_monthly - Set a monthly breakout level\n"
        "🔹 /remove - Stop tracking a company\n"
        "🔹 /status - View all your active trackers\n\n"
        "📊 **Market Data**\n"
        "🔹 /price - Get today's live price and OHLC\n"
        "🔹 /weekly - View the last 8 weekly closes\n"
        "🔹 /daily - View the last 7 daily closes\n"
        "🔹 /monthly - View the last 6 monthly closes\n"
        "🔹 /signal_weekly - Check weekly breakout status\n"
        "🔹 /signal_daily - Check daily breakout status\n"
        "🔹 /signal_monthly - Check monthly breakout status\n"
        "🔹 /breakdown_weekly - See weekly closes below breakout\n"
        "🔹 /breakdown_daily - See daily closes below breakout\n"
        "🔹 /breakdown_monthly - See monthly closes below breakout\n\n"
        "⏰ **Automation**\n"
        "🔹 /monitor_weekly - Start weekly alerts at 3:00 PM and 3:40 PM IST\n"
        "🔹 /monitor_daily - Start daily alerts at 3:00 PM and 3:40 PM IST\n"
        "🔹 /monitor_monthly - Start monthly alerts at 3:00 PM and 3:40 PM IST\n"
        "🔹 /stop_monitor_weekly - Stop weekly alerts\n"
        "🔹 /stop_monitor_daily - Stop daily alerts\n"
        "🔹 /stop_monitor_monthly - Stop monthly alerts\n\n"
        "💡 *Tip:* Type the ticker symbol directly after the command, like `/signal AAPL` or `/set_breakout_daily RELIANCE.NS 2500`."
        + FOOTER,
        parse_mode="Markdown"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    state = get_chat_state(chat_id)

    if not any(state[timeframe] for timeframe in TIMEFRAMES):
        await update.message.reply_text("You are not tracking any companies right now. Use /set_breakout to get started!" + FOOTER)
        return

    msg = "📋 **Your Tracked Stocks**\n\n"
    for timeframe in TIMEFRAMES:
        trackers = state[timeframe]
        if not trackers:
            continue
        msg += f"**{TIMEFRAME_CONFIG[timeframe]['label']}**\n"
        for ticker, data in trackers.items():
            current_price = get_current_price(ticker)
            msg += f"🔸 *{ticker}*\n"
            msg += f"  • Live Price: ₹{current_price}\n"
            msg += f"  • Breakout Level: ₹{data['breakout_level']}\n"
        msg += "\n"

    await update.message.reply_text(msg.strip() + FOOTER, parse_mode="Markdown")


async def handle_price(message, ticker, is_callback=False):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")

        current_price = round(hist["Close"].iloc[-1], 2)
        day_open = round(hist["Open"].iloc[-1], 2)
        day_high = round(hist["High"].iloc[-1], 2)
        day_low = round(hist["Low"].iloc[-1], 2)
        day_close = round(hist["Close"].iloc[-1], 2)

        text = (
            f"📊 {ticker} Price\n\n"
            f"Current Price: ₹{current_price}\n\n"
            f"Day Open: ₹{day_open}\n"
            f"Day High: ₹{day_high}\n"
            f"Day Low: ₹{day_low}\n"
            f"Day Close: ₹{day_close}"
            + FOOTER
        )
        if is_callback:
            await message.edit_text(text)
        else:
            await message.reply_text(text)

    except Exception as e:
        if is_callback:
            await message.edit_text(f"Error fetching data for {ticker}: {str(e)}")
        else:
            await message.reply_text(f"Error fetching data for {ticker}: {str(e)}")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        chat_id = update.message.chat_id
        set_pending_action(chat_id, "price")
        await update.message.reply_text("Send a ticker symbol, for example: /price AAPL")
        return
        
    ticker_input = " ".join(context.args)
    ticker = find_stock_ticker(ticker_input)
    await handle_price(update.message, ticker)


async def handle_history(message, ticker, timeframe, is_callback=False):
    try:
        df = get_timeframe_data(ticker, timeframe).tail(TIMEFRAME_CONFIG[timeframe]["display_count"])
        label = TIMEFRAME_CONFIG[timeframe]["label"]
        msg = f"📅 {ticker} Last {TIMEFRAME_CONFIG[timeframe]['display_count']} {label} Closes\n\n"

        for idx, row in df.iterrows():
            msg += f"{idx.strftime('%d-%b-%Y')} : ₹{round(row['Close'], 2)}\n"

        if is_callback:
            await message.edit_text(msg + FOOTER)
        else:
            await message.reply_text(msg + FOOTER)

    except Exception as e:
        if is_callback:
            await message.edit_text(f"Error: {str(e)}")
        else:
            await message.reply_text(f"Error: {str(e)}")


async def handle_weekly(message, ticker, is_callback=False):
    await handle_history(message, ticker, "weekly", is_callback)


async def handle_daily(message, ticker, is_callback=False):
    await handle_history(message, ticker, "daily", is_callback)


async def handle_monthly(message, ticker, is_callback=False):
    await handle_history(message, ticker, "monthly", is_callback)


async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        chat_id = update.message.chat_id
        set_pending_action(chat_id, "weekly")
        await update.message.reply_text("Send a ticker symbol, for example: /weekly AAPL")
        return
        
    ticker_input = " ".join(context.args)
    ticker = find_stock_ticker(ticker_input)
    await handle_weekly(update.message, ticker)


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        chat_id = update.message.chat_id
        set_pending_action(chat_id, "daily")
        await update.message.reply_text("Send a ticker symbol, for example: /daily AAPL")
        return

    ticker_input = " ".join(context.args)
    ticker = find_stock_ticker(ticker_input)
    await handle_daily(update.message, ticker)


async def monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        chat_id = update.message.chat_id
        set_pending_action(chat_id, "monthly")
        await update.message.reply_text("Send a ticker symbol, for example: /monthly AAPL")
        return

    ticker_input = " ".join(context.args)
    ticker = find_stock_ticker(ticker_input)
    await handle_monthly(update.message, ticker)


async def handle_breakout_signal(message, chat_id, ticker, timeframe, is_callback=False):
    try:
        breakout_level = get_breakout_level(chat_id, timeframe, ticker)
        
        if breakout_level is None:
            err = f"No breakout level set for {ticker} in {TIMEFRAME_CONFIG[timeframe]['label'].lower()} mode. Use /set_breakout_{timeframe} <price> to set one." + FOOTER
            if is_callback:
                await message.edit_text(err)
            else:
                await message.reply_text(err)
            return
            
        signal_date = get_signal_date(chat_id, timeframe, ticker)
        info = get_breakout_info(ticker, timeframe, breakout_level, signal_date)
        current_price = get_current_price(ticker)
        
        signal_date_str = signal_date.strftime('%d-%b-%Y %I:%M %p')
        timeframe_label = TIMEFRAME_CONFIG[timeframe]["label"]

        msg = (
            f"🚦 {ticker} {timeframe_label.upper()} SIGNAL\n\n"
            f"Signal Date: {signal_date_str}\n"
            f"Live Price: ₹{current_price}\n"
            f"Buy Price: {timeframe_label} close above ₹{breakout_level}\n\n"
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
                f"Triggered {timeframe_label}: {info['candle_date']}\n"
                f"Difference: {diff_percent}% (from ₹{breakout_level})"
            )

        if is_callback:
            await message.edit_text(msg + FOOTER)
        else:
            await message.reply_text(msg + FOOTER)

    except Exception as e:
        if is_callback:
            await message.edit_text(f"Error: {str(e)}")
        else:
            await message.reply_text(f"Error: {str(e)}")


async def request_timeframe_company(update, context, action, timeframe):
    chat_id = update.message.chat_id
    set_pending_action(chat_id, f"{action}_{timeframe}")
    await update.message.reply_text(
        f"Send a ticker symbol, for example: /{action}_{timeframe} AAPL"
    )
    return True


async def handle_timeframe_signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE, timeframe):
    if not context.args:
        await request_timeframe_company(update, context, "signal", timeframe)
        return

    ticker_input = " ".join(context.args)
    ticker = find_stock_ticker(ticker_input)
    await handle_breakout_signal(update.message, update.message.chat_id, ticker, timeframe)


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_timeframe_signal_command(update, context, "weekly")


async def signal_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_timeframe_signal_command(update, context, "weekly")


async def signal_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_timeframe_signal_command(update, context, "daily")


async def signal_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_timeframe_signal_command(update, context, "monthly")


async def handle_breakdown(message, chat_id, ticker, timeframe, is_callback=False):
    try:
        breakout_level = get_breakout_level(chat_id, timeframe, ticker)
        
        if breakout_level is None:
            err = f"No breakout level set for {ticker} in {TIMEFRAME_CONFIG[timeframe]['label'].lower()} mode." + FOOTER
            if is_callback:
                await message.edit_text(err)
            else:
                await message.reply_text(err)
            return
            
        df = get_timeframe_data(ticker, timeframe).tail(TIMEFRAME_CONFIG[timeframe]["display_count"])
        timeframe_label = TIMEFRAME_CONFIG[timeframe]["label"]
        msg = f"⚠ {ticker} Last {timeframe_label} Closes Below ₹{breakout_level}\n\n"

        found = False
        for idx, row in df.iterrows():
            close_price = round(row["Close"], 2)
            if close_price < breakout_level:
                found = True
                msg += f"{idx.strftime('%d-%b-%Y')} : ₹{close_price}\n"

        if not found:
            msg += f"No breakdown candles found in the last {timeframe_label.lower()} window."

        if is_callback:
            await message.edit_text(msg + FOOTER)
        else:
            await message.reply_text(msg + FOOTER)

    except Exception as e:
        if is_callback:
            await message.edit_text(f"Error: {str(e)}")
        else:
            await message.reply_text(f"Error: {str(e)}")


async def handle_timeframe_breakdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE, timeframe):
    if not context.args:
        await request_timeframe_company(update, context, "breakdown", timeframe)
        return

    ticker_input = " ".join(context.args)
    ticker = find_stock_ticker(ticker_input)
    await handle_breakdown(update.message, update.message.chat_id, ticker, timeframe)


async def breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_timeframe_breakdown_command(update, context, "weekly")


async def breakdown_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_timeframe_breakdown_command(update, context, "weekly")


async def breakdown_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_timeframe_breakdown_command(update, context, "daily")


async def breakdown_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_timeframe_breakdown_command(update, context, "monthly")


async def handle_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE, timeframe):
    chat_id = update.message.chat_id
    state = get_timeframe_state(chat_id, timeframe)

    if not state:
        await update.message.reply_text(f"You are not tracking any {TIMEFRAME_CONFIG[timeframe]['label'].lower()} companies." + FOOTER)
        return

    if not context.args:
        set_pending_action(chat_id, f"remove_{timeframe}")
        await update.message.reply_text(
            f"Send a {TIMEFRAME_CONFIG[timeframe]['label'].lower()}-tracked ticker symbol, for example: /remove_{timeframe} AAPL"
        )
        return

    ticker_input = " ".join(context.args)
    ticker = find_stock_ticker(ticker_input)

    if ticker in state:
        del state[ticker]
        await update.message.reply_text(f"🗑️ Stopped tracking {ticker}." + FOOTER)
    else:
        await update.message.reply_text(f"You are not tracking {ticker}." + FOOTER)


async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_remove_command(update, context, "weekly")


async def remove_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_remove_command(update, context, "weekly")


async def remove_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_remove_command(update, context, "daily")


async def remove_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_remove_command(update, context, "monthly")


async def set_breakout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_set_breakout_command(update, context, "weekly")


async def handle_set_breakout_command(update: Update, context: ContextTypes.DEFAULT_TYPE, timeframe):
    try:
        if len(context.args) == 0:
            await update.message.reply_text(
                f"Send the ticker symbol and breakout level, for example: /set_breakout_{timeframe} AAPL 2300" + FOOTER
            )
            return
            
        chat_id = update.message.chat_id
        level = None
        ticker_parts = []
        for arg in context.args:
            try:
                level = float(arg)
            except ValueError:
                ticker_parts.append(arg)

        if level is None or not ticker_parts:
            await update.message.reply_text(
                f"Use both ticker symbol and price, for example: /set_breakout_{timeframe} AAPL 2300" + FOOTER
            )
            return

        ticker = find_stock_ticker(" ".join(ticker_parts))
        
        set_breakout_level(chat_id, timeframe, ticker, level)
        await update.message.reply_text(f"✅ {TIMEFRAME_CONFIG[timeframe]['label']} breakout level for {ticker} updated to ₹{level}" + FOOTER)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid number format." + FOOTER)


async def set_breakout_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_set_breakout_command(update, context, "weekly")


async def set_breakout_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_set_breakout_command(update, context, "daily")


async def set_breakout_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_set_breakout_command(update, context, "monthly")


def get_monitor_job_name(chat_id, timeframe, slot):
    return f"{chat_id}:{timeframe}:{slot}"


async def check_breakout_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    timeframe = job.data["timeframe"]
    slot = job.data["slot"]
    now_ist = datetime.now(IST)

    if not should_run_monitor(timeframe, now_ist):
        return

    state = get_timeframe_state(chat_id, timeframe)
    if not state:
        return

    for ticker, data in state.items():
        breakout_level = data["breakout_level"]
        current_price = get_current_price(ticker)
        last_alert_date = data.get("last_alert_date")

        if current_price and current_price > breakout_level and last_alert_date != now_ist.date().isoformat():
            set_last_alert_date(chat_id, timeframe, ticker, now_ist.date().isoformat())
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🚨 {TIMEFRAME_CONFIG[timeframe]['label'].upper()} BREAKOUT ALERT [{slot}] 🚨\n\n"
                    f"{ticker} is currently trading above ₹{breakout_level}!\n"
                    f"Current Price: ₹{current_price}"
                    + FOOTER
                )
            )


def clear_monitor_jobs(context, chat_id, timeframe):
    for slot in MONITOR_TIMES:
        current_jobs = context.job_queue.get_jobs_by_name(get_monitor_job_name(chat_id, timeframe, slot))
        for job in current_jobs:
            job.schedule_removal()


def schedule_monitor_jobs(context, chat_id, timeframe):
    for slot in MONITOR_TIMES:
        hour = 15
        minute = 0 if slot == "1500" else 40
        context.job_queue.run_daily(
            check_breakout_job,
            time=dt_time(hour, minute, tzinfo=IST),
            days=(0, 1, 2, 3, 4, 5, 6),
            chat_id=chat_id,
            name=get_monitor_job_name(chat_id, timeframe, slot),
            data={"timeframe": timeframe, "slot": slot},
        )


async def monitor_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE, timeframe):
    chat_id = update.message.chat_id
    state = get_timeframe_state(chat_id, timeframe)

    if not state:
        await update.message.reply_text(f"You are not tracking any {TIMEFRAME_CONFIG[timeframe]['label'].lower()} companies yet." + FOOTER)
        return

    clear_monitor_jobs(context, chat_id, timeframe)
    schedule_monitor_jobs(context, chat_id, timeframe)
    await update.message.reply_text(
        f"✅ {TIMEFRAME_CONFIG[timeframe]['label']} monitoring started! I will check at 3:00 PM and 3:40 PM IST." + FOOTER
    )


async def stop_monitor_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE, timeframe):
    chat_id = update.message.chat_id
    clear_monitor_jobs(context, chat_id, timeframe)
    await update.message.reply_text(f"⏹️ {TIMEFRAME_CONFIG[timeframe]['label']} monitoring stopped." + FOOTER)


async def monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await monitor_timeframe(update, context, "weekly")


async def monitor_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await monitor_timeframe(update, context, "weekly")


async def monitor_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await monitor_timeframe(update, context, "daily")


async def monitor_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await monitor_timeframe(update, context, "monthly")


async def stop_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_monitor_timeframe(update, context, "weekly")


async def stop_monitor_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_monitor_timeframe(update, context, "weekly")


async def stop_monitor_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_monitor_timeframe(update, context, "daily")


async def stop_monitor_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_monitor_timeframe(update, context, "monthly")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    command = data[0]
    ticker = data[1]
    
    chat_id = query.message.chat_id
    clear_pending_action(chat_id)
    timeframe = get_target_timeframe_from_command(command)
    
    if command == "price":
        await handle_price(query.message, ticker, is_callback=True)
    elif command in {"weekly", "daily", "monthly"}:
        await handle_history(query.message, ticker, command, is_callback=True)
    elif command.startswith("signal_"):
        await handle_breakout_signal(query.message, chat_id, ticker, timeframe, is_callback=True)
    elif command.startswith("breakdown_"):
        await handle_breakdown(query.message, chat_id, ticker, timeframe, is_callback=True)
    elif command.startswith("set_"):
        level = float(data[2])
        set_breakout_level(chat_id, timeframe, ticker, level)
        await query.message.edit_text(f"✅ {TIMEFRAME_CONFIG[timeframe]['label']} breakout level for {ticker} updated to ₹{level}" + FOOTER)
    elif command.startswith("remove_"):
        state = get_timeframe_state(chat_id, timeframe)
        if ticker in state:
            del state[ticker]
            await query.message.edit_text(f"🗑️ Stopped tracking {ticker}." + FOOTER)
        else:
            await query.message.edit_text(f"You are not tracking {ticker}." + FOOTER)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None or not message.text:
        return

    chat_id = message.chat_id
    action = get_pending_action(chat_id)
    if not action:
        return

    ticker = find_stock_ticker(message.text)
    clear_pending_action(chat_id)

    parts = action.split("_")
    base_action = parts[0]
    timeframe = parts[1] if len(parts) > 1 else "weekly"

    if base_action == "price":
        await handle_price(message, ticker)
    elif base_action in {"weekly", "daily", "monthly"}:
        await handle_history(message, ticker, base_action)
    elif base_action == "signal":
        await handle_breakout_signal(message, chat_id, ticker, timeframe)
    elif base_action == "breakdown":
        await handle_breakdown(message, chat_id, ticker, timeframe)
    elif base_action == "set":
        state_timeframe = timeframe if timeframe in TIMEFRAMES else "weekly"
        level = float(message.text)
        set_breakout_level(chat_id, state_timeframe, ticker, level)
        await message.reply_text(f"✅ {TIMEFRAME_CONFIG[state_timeframe]['label']} breakout level for {ticker} updated to ₹{level}" + FOOTER)
    elif base_action == "remove":
        state = get_timeframe_state(chat_id, timeframe)
        if ticker in state:
            del state[ticker]
            await message.reply_text(f"🗑️ Stopped tracking {ticker}." + FOOTER)
        else:
            await message.reply_text(f"You are not tracking {ticker}." + FOOTER)


async def post_init(application: Application):
    await application.bot.set_my_commands([
        ("start", "Start the bot and see instructions"),
        ("status", "View all your active tracked stocks"),
        ("price", "Get today's live price and OHLC"),
        ("weekly", "View the last 8 weekly closes"),
        ("daily", "View the last 7 daily closes"),
        ("monthly", "View the last 6 monthly closes"),
        ("signal", "Check weekly breakout status"),
        ("signal_weekly", "Check weekly breakout status"),
        ("signal_daily", "Check daily breakout status"),
        ("signal_monthly", "Check monthly breakout status"),
        ("breakdown", "See weekly closes below breakout"),
        ("breakdown_weekly", "See weekly closes below breakout"),
        ("breakdown_daily", "See daily closes below breakout"),
        ("breakdown_monthly", "See monthly closes below breakout"),
        ("set_breakout", "Set weekly breakout level"),
        ("set_breakout_weekly", "Set weekly breakout level"),
        ("set_breakout_daily", "Set daily breakout level"),
        ("set_breakout_monthly", "Set monthly breakout level"),
        ("remove", "Stop tracking a company"),
        ("remove_weekly", "Stop tracking a weekly company"),
        ("remove_daily", "Stop tracking a daily company"),
        ("remove_monthly", "Stop tracking a monthly company"),
        ("monitor", "Start weekly alerts"),
        ("monitor_weekly", "Start weekly alerts"),
        ("monitor_daily", "Start daily alerts"),
        ("monitor_monthly", "Start monthly alerts"),
        ("stop_monitor", "Stop weekly alerts"),
        ("stop_monitor_weekly", "Stop weekly alerts"),
        ("stop_monitor_daily", "Stop daily alerts"),
        ("stop_monitor_monthly", "Stop monthly alerts")
    ])

# -------------------------
# MAIN
# -------------------------

def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("weekly", weekly))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("monthly", monthly))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("signal_weekly", signal_weekly))
    app.add_handler(CommandHandler("signal_daily", signal_daily))
    app.add_handler(CommandHandler("signal_monthly", signal_monthly))
    app.add_handler(CommandHandler("breakdown", breakdown))
    app.add_handler(CommandHandler("breakdown_weekly", breakdown_weekly))
    app.add_handler(CommandHandler("breakdown_daily", breakdown_daily))
    app.add_handler(CommandHandler("breakdown_monthly", breakdown_monthly))
    app.add_handler(CommandHandler("set_breakout", set_breakout))
    app.add_handler(CommandHandler("set_breakout_weekly", set_breakout_weekly))
    app.add_handler(CommandHandler("set_breakout_daily", set_breakout_daily))
    app.add_handler(CommandHandler("set_breakout_monthly", set_breakout_monthly))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("remove_weekly", remove_weekly))
    app.add_handler(CommandHandler("remove_daily", remove_daily))
    app.add_handler(CommandHandler("remove_monthly", remove_monthly))
    app.add_handler(CommandHandler("monitor", monitor))
    app.add_handler(CommandHandler("monitor_weekly", monitor_weekly))
    app.add_handler(CommandHandler("monitor_daily", monitor_daily))
    app.add_handler(CommandHandler("monitor_monthly", monitor_monthly))
    app.add_handler(CommandHandler("stop_monitor", stop_monitor))
    app.add_handler(CommandHandler("stop_monitor_weekly", stop_monitor_weekly))
    app.add_handler(CommandHandler("stop_monitor_daily", stop_monitor_daily))
    app.add_handler(CommandHandler("stop_monitor_monthly", stop_monitor_monthly))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling()


if __name__ == "__main__":
    main()