import os
import io
import requests
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from google import genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# OCR.space - مجاني وخفيف، مش بيحتاج تحميل
OCR_API_KEY = "helloworld"  # مفتاح مجاني تجريبي، شغال على طول

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بيك!\n\n"
        "ابعتلي أي صورة فيها نص، وهقراهولك في ثواني.\n"
        "بيدعم العربي والإنجليزي."
    )

def ocr_space(img_bytes):
    """قراءة سريعة بـ OCR.space - زي البوت التاني بالظبط"""
    try:
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("image.jpg", img_bytes, "image/jpeg")},
            data={
                "apikey": OCR_API_KEY,
                "language": "ara",  # عربي
                "isOverlayRequired": False,
                "scale": True,
                "OCREngine": 2,  # المحرك الجديد الأسرع
            },
            timeout=30
        )
        data = r.json()
        if data.get("ParsedResults"):
            text = data["ParsedResults"][0].get("ParsedText", "").strip()
            return text
    except Exception as e:
        print(f"OCR.space error: {e}")
    return ""

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري القراءة... ثواني")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))

        # 1. جرب OCR.space الأول - سريع وخفيف
        text = ocr_space(bytes(img_bytes))

        # لو النص طلع إنجليزي بس أو فاضي، جرب تاني بالإنجليزي
        if not text:
            try:
                r = requests.post(
                    "https://api.ocr.space/parse/image",
                    files={"file": ("image.jpg", bytes(img_bytes), "image/jpeg")},
                    data={"apikey": OCR_API_KEY, "language": "eng", "OCREngine": 2},
                    timeout=30
                )
                text = r.json()["ParsedResults"][0]["ParsedText"].strip()
            except:
                pass

        # 2. لو OCR معرفش، جرب Gemini احتياطي
        if not text and client:
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=["استخرج النص من الصورة بالظبط، بدون شرح.", img]
                )
                text = response.text.strip()
            except:
                pass

        if text:
            await update.message.reply_text(f"✅ النص:\n\n{text}")
        else:
            await update.message.reply_text("❌ معرفتش أقرأ النص، جرب صورة أوضح.")

    except Exception as e:
        await update.message.reply_text(f"❌ حصل خطأ: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📷 ابعتلي صورة، وأنا هقرأ النص اللي فيها.")

def main():
    if not TELEGRAM_TOKEN:
        print("❌ مفيش TELEGRAM_BOT_TOKEN")
        return
    print("✅ البوت شغال...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
