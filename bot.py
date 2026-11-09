import os
import io
import asyncio
import base64
import requests
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from google import genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بيك!\n\nابعتلي أي صورة، وهقراهالك في ثواني.")

def call_groq(img_bytes):
    # Groq - سريع جداً، 2-5 ثواني، مش بيقول مضغوط
    try:
        b64 = base64.b64encode(img_bytes).decode()
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "استخرج النص من الصورة بالظبط، بدون شرح، بنفس الترتيب."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]
                }],
                "max_tokens": 500,
                "temperature": 0
            },
            timeout=40
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return None

def call_gemini(img):
    try:
        r = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=["استخرج النص من الصورة بالظبط، بدون شرح.", img]
        )
        return r.text.strip()
    except:
        return None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري القراءة... ثواني")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024))

        # شغل Groq و Gemini في نفس الوقت، وخد أول واحد ينجح بجد مش أول واحد يخلص
        tasks = [
            asyncio.to_thread(call_groq, bytes(img_bytes)),
            asyncio.to_thread(call_gemini, img),
        ]
        # استنى 55 ثانية بالكتير
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=55)

        text = None
        for res in results:
            if isinstance(res, str) and len(res.strip()) > 1:
                text = res.strip()
                break

        if text:
            await update.message.reply_text(f"✅ النص:\n\n{text}")
        else:
            await update.message.reply_text("❌ حصل ضغط، جرب تاني بعد 10 ثواني.")

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
