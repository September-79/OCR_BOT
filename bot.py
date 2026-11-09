import os, io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
from google import genai

TOKEN = os.getenv("TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بيك!\n\n"
        "ابعتلي أي صورة فيها نص، وأنا هستخرجلك النص بالظبط.\n"
        "بقرأ عربي مزخرف، خط إيد، سكرين شوت، أي حاجة ✅"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري قراءة الصورة بذكاء اصطناعي... ثواني")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "استخرج كل النص الموجود في هذه الصورة بالظبط كما هو، بدون أي شرح إضافي. حافظ على اللغة الأصلية والترتيب. لو مفيش نص، قول: لا يوجد نص.",
                img
            ]
        )
        text = response.text.strip()
        await update.message.reply_text(f"✅ النص:\n\n{text}")
    except Exception as e:
        await update.message.reply_text(f"❌ حصل خطأ: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("البوت شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()
