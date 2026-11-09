import os
import io
import asyncio
import requests
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from google import genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بيك!\n\nابعتلي أي صورة، وهقراهالك في أقل من دقيقة.")

def call_gemini(model, img):
    try:
        r = client.models.generate_content(
            model=model,
            contents=["استخرج النص من الصورة بالظبط، بدون شرح.", img]
        )
        return r.text.strip()
    except:
        return None

def call_ocr_space(img_bytes):
    try:
        r = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("img.jpg", img_bytes, "image/jpeg")},
            data={"apikey": "helloworld", "language": "ara", "OCREngine": 2, "scale": True},
            timeout=25
        )
        t = r.json()["ParsedResults"][0]["ParsedText"].strip()
        return t if len(t) > 2 else None
    except:
        return None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري القراءة... أقل من دقيقة")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024))

        # شغل 3 محاولات في نفس الوقت، مش ورا بعض
        # اللي يخلص الأول هناخده ونلغي الباقي
        tasks = [
            asyncio.to_thread(call_gemini, "gemini-3.8-flash", img),
            asyncio.to_thread(call_gemini, "gemini-3-flash-preview", img),
            asyncio.to_thread(call_ocr_space, bytes(img_bytes)),
        ]

        text = None
        # استنى 55 ثانية بالكتير، وبعدها وقف كله
        done, pending = await asyncio.wait(
            [asyncio.create_task(t) for t in tasks],
            timeout=55,
            return_when=asyncio.FIRST_COMPLETED
        )

        for d in done:
            try:
                res = d.result()
                if res:
                    text = res
                    break
            except:
                pass

        # لو أول واحد فشل، استنى الباقي شوية
        if not text:
            for p in pending:
                try:
                    res = await asyncio.wait_for(p, timeout=10)
                    if res:
                        text = res
                        break
                except:
                    pass

        # الغي اللي لسه شغال
        for p in pending:
            p.cancel()

        if text:
            await update.message.reply_text(f"✅ النص:\n\n{text}")
        else:
            await update.message.reply_text("❌ جوجل مضغوط، جرب تاني بعد دقيقة.")

    except Exception as e:
        await update.message.reply_text(f"❌ حصل خطأ: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📷 ابعتلي صورة.")

def main():
    print("✅ البوت شغال...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
