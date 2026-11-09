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
    await update.message.reply_text("👋 أهلاً بيك!\n\nابعتلي أي صورة.")

def compress_image(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    if max(img.size) > 800:
        img.thumbnail((800, 800))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue(), img

def call_groq(img_bytes):
    # الموديلات الجديدة اللي شغالة في Groq دلوقتي - مش Llama
    b64 = base64.b64encode(img_bytes).decode()
    for model in ["qwen/qwen3.6-27b", "qwen/qwen3.8-27b", "qwen/qwen3-vl-32b-instruct"]:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "استخرج النص من الصورة بالظبط، بدون شرح."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
                    "max_tokens": 500,
                    "temperature": 0
                },
                timeout=40
            )
            print(f"Groq {model} -> {r.status_code}")
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            else:
                print(f"Groq error: {r.text[:400]}")
        except Exception as e:
            print(f"Groq {model} exception: {e}")
    return None

def call_gemini(img):
    try:
        r = client.models.generate_content(model="gemini-3.8-flash", contents=["استخرج النص من الصورة بالظبط، بدون شرح.", img])
        return r.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري القراءة... ثواني")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        small_bytes, img = compress_image(bytes(img_bytes))

        text = await asyncio.to_thread(call_groq, small_bytes)
        if not text:
            text = await asyncio.to_thread(call_gemini, img)

        if text:
            await update.message.reply_text(f"✅ النص:\n\n{text}")
        else:
            await update.message.reply_text("❌ فشل، جرب تاني.")
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
