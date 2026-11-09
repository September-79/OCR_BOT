import os
import io
import asyncio
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from google import genai

# المفتاح بيجي من FadeHost - بنجرب الاسمين عشان ميوقفش تاني
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
    await update.message.reply_text("⏳ جاري قراءة الصورة بذكاء اصطناعي... ثواني")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))

        # جوجل سمح بس بموديلات 3.x للمستخدمين الجدد
        models = [
            "gemini-3.8-flash",
            "gemini-3-flash-preview",
            "gemini-3-pro-preview",
            "gemini-3.8-flash-preview",
        ]

        text = None
        last_error = ""

        for model in models:
            for attempt in range(3):  # جرب نفس الموديل 3 مرات
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            "استخرج كل النص الموجود في هذه الصورة بالظبط كما هو، بدون أي شرح إضافي. حافظ على اللغة الأصلية والترتيب. لو مفيش نص، قول: لا يوجد نص.",
                            img
                        ]
                    )
                    text = response.text.strip()
                    break
                except Exception as e:
                    last_error = str(e)
                    # لو زحمة 503 استنى 5 ثواني وجرب تاني
                    if "503" in str(e) or "UNAVAILABLE" in str(e) or "overloaded" in str(e).lower():
                        await asyncio.sleep(5)
                        continue
                    break
            if text:
                break

        if text:
            await update.message.reply_text(f"✅ النص:\n\n{text}")
        else:
            await update.message.reply_text("❌ جوجل مضغوط دلوقتي، استنى دقيقتين وابعت الصورة تاني.")

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
