from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

BREAKOUT_LEVEL = 2260

FOOTER = "\n\n━━━━━━━━━━━━\nCreated by Sai Venkatesh"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"📈 TCS Weekly Tracker Active\n\n"
"Commands:\n"
"/start\n"
"/status\n"
"/price\n"
"/weekly\n"
"/signal\n"
"/breakdown"
+ FOOTER
)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
current_price = get_current_price()

```
    await update.message.reply_text(
        f"📈 TCS Weekly Tracker\n\n"
        f"Signal Date: {datetime.now().strftime('%d-%b-%Y %H:%M')}\n\n"
        f"Live Price: ₹{current_price}\n"
        f"Breakout Level: ₹{BREAKOUT_LEVEL}"
        + FOOTER
    )

except Exception as e:
    await update.message.reply_text(
        f"Error: {str(e)}" + FOOTER
    )
```

def get_current_price():
tcs = yf.Ticker("TCS.NS")
hist = tcs.history(period="5d")
return round(hist["Close"].iloc[-1], 2)

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
tcs = yf.Ticker("TCS.NS")
hist = tcs.history(period="5d")

```
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
```

async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
tcs = yf.Ticker("TCS.NS")
df = tcs.history(period="3mo", interval="1wk")

```
    message = "📅 Last 8 Weekly Closes\n\n"

    for idx, row in df.tail(8).iterrows():
        message += (
            f"{idx.strftime('%d-%b-%Y')} : "
            f"₹{round(row['Close'], 2)}\n"
        )

    await update.message.reply_text(
        message + FOOTER
    )

except Exception as e:
    await update.message.reply_text(
        f"Error: {str(e)}" + FOOTER
    )
```

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
tcs = yf.Ticker("TCS.NS")

```
    weekly_df = tcs.history(
        start="2026-03-01",
        interval="1wk"
    )

    breakout_found = False
    breakout_price = None
    breakout_week = None

    for idx, row in weekly_df.iterrows():
        close_price = round(row["Close"], 2)

        if close_price > BREAKOUT_LEVEL:
            breakout_found = True
            breakout_price = close_price
            breakout_week = idx.strftime("%d-%b-%Y")
            break

    current_price = get_current_price()

    if breakout_found:

        gain = round(
            ((current_price - breakout_price)
             / breakout_price) * 100,
            2
        )

        msg = (
            "🚦 TCS SIGNAL\n\n"
            "Status: ✅ Breakout Done\n\n"
            f"Buy Price: ₹{breakout_price}\n"
            f"Breakout Week: {breakout_week}\n"
            f"Current Price: ₹{current_price}\n"
            f"Return: {gain}%"
        )

    else:

        msg = (
            "🚦 TCS SIGNAL\n\n"
            "Status: ⏳ Monitoring\n\n"
            f"Level: ₹{BREAKOUT_LEVEL}\n"
            f"Current Price: ₹{current_price}"
        )

    await update.message.reply_text(
        msg + FOOTER
    )

except Exception as e:
    await update.message.reply_text(
        f"Error: {str(e)}" + FOOTER
    )
```

async def breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
try:
tcs = yf.Ticker("TCS.NS")
df = tcs.history(period="2mo", interval="1wk")

```
    message = (
        f"⚠ Weekly Closes Below ₹{BREAKOUT_LEVEL}\n\n"
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
        message += "No breakdown candles found."

    await update.message.reply_text(
        message + FOOTER
    )

except Exception as e:
    await update.message.reply_text(
        f"Error: {str(e)}" + FOOTER
    )
```

def main():
app = Application.builder().token(BOT_TOKEN).build()

```
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("weekly", weekly))
app.add_handler(CommandHandler("signal", signal))
app.add_handler(CommandHandler("breakdown", breakdown))

app.run_polling()
```

if **name** == "**main**":
main()

