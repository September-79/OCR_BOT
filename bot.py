import os
import io
import asyncio
import numpy as np
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# OCR - بيشتغل عندك مش عند جوجل، فمفيش زحمة
import easyocr

print("⏳ جاري تحميل محرك القراءة... أول مرة بس هتاخد دقيقة")
reader = easyocr.Reader(['ar', 'en'], gpu=False, verbose=False)
print("✅ محرك القراءة جاهز")

# Gemini احتياطي بس
from google import genai
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بيك!\n\n"
        "ابعتلي أي صورة فيها نص، وهقراهولك في ثواني.\n"
        "بيدعم العربي والإنجليزي."
    )

def ocr_read(img_pil):
    # EasyOCR بيحتاج numpy
    img_np = np.array(img_pil.convert("RGB"))
    results = reader.readtext(img_np, paragraph=True)
    # رتب من فوق لتحت
    texts = [t for _, t, _ in results]
    return "\n".join(texts).strip()

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري القراءة... ثواني")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))

        # 1. جرب OCR الأول - ده السريع زي البوت التاني
        text = await asyncio.to_thread(ocr_read, img)

        # 2. لو OCR معرفش يقرأ، جرب Gemini احتياطي
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
            await update.message.reply_text("❌ معرفتش أقرأ النص في الصورة دي، جرب صورة أوضح.")

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
