import os
import io
import numpy as np
from PIL import Image, ImageOps
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from google import genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# RapidOCR - خفيف 40 ميجا بس، وبيشتغل عندك مش عند جوجل
from rapidocr_onnxruntime import RapidOCR
engine = RapidOCR()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بيك!\n\n"
        "ابعتلي أي صورة فيها نص، وهقراهولك في ثواني.\n"
        "بيدعم العربي والإنجليزي."
    )

def read_with_rapid(img_pil):
    # لو الخلفية سودا والنص أبيض، اقلبها عشان الـ OCR يقراها
    # دي كانت مشكلة صورتك
    img = img_pil.convert("RGB")
    # جرب الصورة الأصلية
    for test_img in [img, ImageOps.invert(img)]:
        result, _ = engine(np.array(test_img))
        if result:
            # رتب من فوق لتحت
            result = sorted(result, key=lambda x: x[1][0][1])
            text = "\n".join([t[1] for t in result]).strip()
            if len(text) > 2:
                return text
    return ""

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري القراءة... ثواني")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))

        # 1. RapidOCR الأول - سريع زي البوت التاني
        text = read_with_rapid(img)

        # 2. لو معرفش، Gemini احتياطي مرة واحدة بس
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
