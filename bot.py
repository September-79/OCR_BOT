import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import pytesseract
import io

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بيك!\n\n"
        "ابعتلي أي صورة فيها نص، وأنا هستخرجلك النص.\n"
        "بدعم العربي والإنجليزي ✅"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري قراءة الصورة... ثواني")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(img, lang='ara+eng').strip()
        if not text:
            await update.message.reply_text("😅 مش لاقي نص واضح، جرب صورة أوضح")
            return
        if len(text) > 4000:
            text = text[:4000] + "\n\n... النص طويل وتم قصه"
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
