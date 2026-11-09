import os
import io
import asyncio
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from google import genai

GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")

client = genai.Client(api_key=GEMINI_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بيك!\n\n"
        "ابعتلي أي صورة فيها نص، وهقراهولك بالظبط.\n"
        "بيدعم العربي والإنجليزي."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = await update.message.reply_text("⏳ جاري القراءة... ممكن تاخد دقيقة عشان جوجل زحمة")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))

        # صغر الصورة عشان تتبعت أسرع
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024))

        # الترتيب ده مهم: 3.8 الأول، وبعدين الـ Pro اللي عليه ضغط أقل
        models = [
            "gemini-3.8-flash",
            "gemini-3-flash-preview",
            "gemini-3-pro-preview",
        ]

        text = None

        for model in models:
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            "استخرج النص من الصورة بالظبط، بدون شرح.",
                            img
                        ]
                    )
                    text = response.text.strip()
                    break
                except Exception as e:
                    err = str(e)
                    if "503" in err or "UNAVAILABLE" in err or "overloaded" in err.lower():
                        # استنى 10 ثواني، عشان جوجل يفضى
                        await asyncio.sleep(10)
                        continue
                    break
            if text:
                break

        if text:
            await update.message.reply_text(f"✅ النص:\n\n{text}")
        else:
            await update.message.reply_text("❌ جوجل مضغوط دلوقتي، جرب تاني بعد دقيقتين.")

    except Exception as e:
        await update.message.reply_text(f"❌ حصل خطأ: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📷 ابعتلي صورة، وأنا هقرأ النص اللي فيها.")

def main():
    if not TELEGRAM_TOKEN:
        print("❌ مفيش TELEGRAM_BOT_TOKEN")
        return
    if not GEMINI_KEY:
        print("❌ مفيش GEMINI_API_KEY")
        return

    print("✅ البوت شغال...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
