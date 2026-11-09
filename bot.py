import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageOps, ImageEnhance
import pytesseract
import io

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بيك!\n\n"
        "ابعتلي أي صورة فيها نص، وأنا هستخرجلك النص.\n"
        "بدعم العربي والإنجليزي ✅\n\n"
        "نصيحة: ابعت الصورة كـ ملف (File) مش صورة عادية عشان الجودة تبقى أعلى"
    )

def clean_image(img):
    # تحويل لرمادي وتكبير الصورة 2x عشان الكلام الصغير يبان
    img = img.convert("L")
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    # زيادة التباين
    img = ImageEnhance.Contrast(img).enhance(1.5)
    # تحويل لأبيض وأسود
    img = img.point(lambda x: 255 if x > 140 else 0, '1')
    return img.convert("L")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري قراءة الصورة... ثواني")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()
        img = Image.open(io.BytesIO(img_bytes))
        img = clean_image(img)
        # psm 6 = اقرأ الصورة كأنها بلوك نص كامل، أحسن للعربي
        text = pytesseract.image_to_string(img, lang='ara+eng', config='--psm 6').strip()
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
