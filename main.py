from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
import yfinance as yf

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

FOOTER = "\n\n━━━━━━━━━━━━\nCreated by Sai Venkatesh"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"📈 TCS Tracker Active\n\n"
"/start\n"
"/status\n"
"/price\n"
"/weekly"
+ FOOTER
)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
"📈 TCS Tracker Running\nBreakout Level: ₹2260"
+ FOOTER
)

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
tcs = yf.Ticker("TCS.NS")
hist = tcs.history(period="5d")

```
current_price = round(hist["Close"].iloc[-1], 2)

await update.message.reply_text(
    f"Current TCS Price: ₹{current_price}"
    + FOOTER
)
```

async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
tcs = yf.Ticker("TCS.NS")
df = tcs.history(period="3mo", interval="1wk")

```
message = "📅 Weekly Closes\n\n"

for idx, row in df.tail(8).iterrows():
    message += f"{idx.strftime('%d-%b-%Y')} : ₹{round(row['Close'],2)}\n"

await update.message.reply_text(message + FOOTER)
```

def main():
app = Application.builder().token(BOT_TOKEN).build()

```
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("weekly", weekly))

app.run_polling()
```

if **name** == "**main**":
main()
