from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

BREAKOUT_LEVEL = 2260
START_DATE = "2026-03-01"

FOOTER = "\n\n━━━━━━━━━━━━\nCreated by Sai Venkatesh"

def get_weekly_data():
ticker = yf.Ticker("TCS.NS")
return ticker.history(start=START_DATE, interval="1wk")

def get_current_price():
ticker = yf.Ticker("TCS.NS")
hist = ticker.history(period="5d")

```
if len(hist) == 0:
    return None

return round(hist["Close"].iloc[-1], 2)
```

def get_breakout_info():
weekly = get_weekly_data()

```
for idx, row in weekly.iterrows():
    close_price = round(row["Close"], 2)

    if close_price > BREAKOUT_LEVEL:
        return {
            "status": "✅ Breakout Done",
            "buy_price": close_price,
            "breakout_week": idx.strftime("%d-%b-%Y")
        }

return {
    "status": "⏳ Monitoring",
    "buy_price": None,
    "breakout_week": None
}
```

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"📈 TCS Weekly Tracker Active\n\n"
"Commands:\n"
"/status\n"
"/signal\n"
"/price\n"
"/weekly\n"
"/breakdown"
+ FOOTER
)

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
info = get_breakout_info()

```
if info["buy_price"] is None:
    message = (
        "🚦 TCS SIGNAL\n\n"
        f"Level: ₹{BREAKOUT_LEVEL}\n\n"
        f"Status: {info['status']}"
        + FOOTER
    )
else:
    current_price = get_current_price()

    gain = round(
        ((current_price - info["buy_price"])
         / info["buy_price"]) * 100,
        2
    )

    message = (
        "🚦 TCS SIGNAL\n\n"
        f"Level: ₹{BREAKOUT_LEVEL}\n\n"
        f"Status: {info['status']}\n\n"
        f"Buy Price: ₹{info['buy_price']}\n"
        f"Return: {gain}%"
        + FOOTER
    )

await update.message.reply_text(message)
```

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
info = get_breakout_info()

```
current_price = get_current_price()

message = (
    "📈 TCS Weekly Tracker\n\n"
    f"Signal Date: {datetime.now().strftime('%d-%b-%Y %H:%M')}\n\n"
    f"Live Price: ₹{current_price}\n"
    f"Breakout Level: ₹{BREAKOUT_LEVEL}\n"
    f"Status: {info['status']}\n\n"
)

if info["buy_price"] is not None:
    gain = round(
        ((current_price - info["buy_price"])
         / info["buy_price"]) * 100,
        2
    )

    message += (
        f"Buy Price: ₹{info['buy_price']}\n"
        f"Breakout Week: {info['breakout_week']}\n"
        f"Return: {gain}%"
    )

message += FOOTER

await update.message.reply_text(message)
```

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
tcs = yf.Ticker("TCS.NS")
hist = tcs.history(period="5d")

```
    current_price = round(hist["Close"].iloc[-1], 2)
    day_high = round(hist["High"].iloc[-1], 2)
    day_low = round(hist["Low"].iloc[-1], 2)

    nifty = yf.Ticker("^NSEI")
    nifty_hist = nifty.history(period="5d")
    nifty_price = round(nifty_hist["Close"].iloc[-1], 2)

    await update.message.reply_text(
        "📊 Market Snapshot\n\n"
        f"TCS\n"
        f"Current Price: ₹{current_price}\n"
        f"Day High: ₹{day_high}\n"
        f"Day Low: ₹{day_low}\n\n"
        f"NIFTY 50\n"
        f"Current Value: {nifty_price}"
        + FOOTER
    )

except Exception as e:
    await update.message.reply_text(
        f"Error:\n{str(e)}"
        + FOOTER
    )
```

async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
weekly_df = get_weekly_data().tail(8)

```
message = "📅 Last 8 Weekly Closes\n\n"

for idx, row in weekly_df.iterrows():
    message += (
        f"{idx.strftime('%d-%b-%Y')} : "
        f"₹{round(row['Close'], 2)}\n"
    )

message += FOOTER

await update.message.reply_text(message)
```

async def breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
weekly_df = get_weekly_data().tail(8)

```
message = (
    f"⚠ Weekly Closes Below ₹{BREAKOUT_LEVEL}\n\n"
)

found = False

for idx, row in weekly_df.iterrows():
    close_price = round(row["Close"], 2)

    if close_price < BREAKOUT_LEVEL:
        found = True

        message += (
            f"{idx.strftime('%d-%b-%Y')} : "
            f"₹{close_price}\n"
        )

if not found:
    message += "No breakdown candles found."

message += FOOTER

await update.message.reply_text(message)
```

def main():
app = Application.builder().token(BOT_TOKEN).build()

```
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("signal", signal))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("weekly", weekly))
app.add_handler(CommandHandler("breakdown", breakdown))

app.run_polling()
```

if **name** == "**main**":
main()
