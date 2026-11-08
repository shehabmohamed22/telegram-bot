import os
import re
import telebot
from flask import Flask
from telebot import types

TOKEN = "9129643719:AAHxxMGZmYvXQHIXYFCxUY88nbhWVPn6plQ"
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

accounts_data = {}


def get_accounts_text():
  if not accounts_data:
    return (
        "📊 **Limits / القائمة الحالية:**\n\n"
        "القائمة فارغة حالياً.\nأرسل القائمة كاملة بالشكل التالي لكل حساب:\n"
        "`01234567891`\n`60000`\n`Name`"
    )

  text = "📊 **Limits / القائمة الحالية:**\n\n"
  for phone, info in accounts_data.items():
    text += f"`{phone}`\n💰 {info['balance']}\n👤 {info['name']}\n\n"
  return text


def get_main_keyboard():
  markup = types.InlineKeyboardMarkup(row_width=2)
  btn_deduct = types.InlineKeyboardButton("➖ خصم يدوي", callback_data="deduct")
  btn_add = types.InlineKeyboardButton("➕ إضافة مبلغ", callback_data="add")
  btn_list = types.InlineKeyboardButton("📋 عرض القائمة", callback_data="show_list")
  btn_clear = types.InlineKeyboardButton("🗑️ مسح الكل", callback_data="clear")
  markup.add(btn_deduct, btn_add, btn_list, btn_clear)
  return markup


@bot.message_handler(commands=["start", "limits", "help"])
def send_welcome(message):
  bot.send_message(
      message.chat.id,
      get_accounts_text(),
      reply_markup=get_main_keyboard(),
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: not message.text.startswith("/") and message.photo is None
)
def handle_text_input(message):
  global accounts_data
  lines = [
      line.strip() for line in message.text.strip().split("\n") if line.strip()
  ]

  if len(lines) >= 3:
    added_count = 0
    i = 0
    while i + 2 < len(lines):
      phone = lines[i]
      try:
        balance = float(lines[i + 1])
        name = lines[i + 2]
        accounts_data[phone] = {"name": name, "balance": balance}
        added_count += 1
        i += 3
      except ValueError:
        i += 1

    if added_count > 0:
      bot.reply_to(
          message,
          f"✅ تم إضافة أو تحديث ({added_count}) حساب بنجاح!\nاضغط على 'عرض القائمة' لرؤيتها.",
          reply_markup=get_main_keyboard(),
      )
    else:
      bot.reply_to(
          message,
          "⚠️ تأكد من تنسيق الإرسال:\nالرقم\nالمبلغ\nالاسم",
          reply_markup=get_main_keyboard(),
      )
  else:
    bot.reply_to(
        message,
        "⚠️ يرجى إرسال البيانات بالترتيب:\nرقم الهاتف\nالمبلغ\nالاسم",
        reply_markup=get_main_keyboard(),
      )


# استقبال الصور ومعالجتها للخصم التلقائي
@bot.message_handler(content_types=["photo"])
def handle_receipt(message):
  global accounts_data
  bot.reply_to(
      message,
      "🔍 جاري تحليل الإيصال...",
      reply_markup=get_main_keyboard(),
  )

  try:
    # تحميل الصورة المرسلة
    fileID = message.photo[-1].file_id
    file_info = bot.get_file(fileID)
    downloaded_file = bot.download_file(file_info.file_path)

    image_path = "temp_receipt.jpg"
    with open(image_path, "wb") as new_file:
      new_file.write(downloaded_file)

    # استخدام مكتبة OCR لقراءة النص من الصورة إذا توفرت، أو محاكاة البحث عن الأرقام
    try:
      import pytesseract
      from PIL import Image

      text = pytesseract.image_to_string(Image.open(image_path))
    except Exception:
      text = ""  # في حال عدم توفر مكتبة tesseract محلياً على السيرفر

    # البحث عن رقم هاتف ومبلغ داخل النص المستخرج أو التعليق المرفق مع الصورة
    caption = message.caption if message.caption else ""
    full_text = text + " " + caption

    # البحث عن رقم يبدأ بـ 01 ويتكون من 11 رقم ومبلغ مالي
    found_phone = None
    for phone in accounts_data.keys():
      if phone in full_text:
        found_phone = phone
        break

    # استخراج المبلغ (أرقام مالية)
    numbers = re.findall(r"\d+", full_text)

    if found_phone and len(numbers) >= 2:
      # محاولة تخمين المبلغ المحول
      deduct_amount = float(
          numbers[-1]
      )  # افتراض أن آخر رقم ظاهر هو المبلغ غالباً
      if accounts_data[found_phone]["balance"] >= deduct_amount:
        accounts_data[found_phone]["balance"] -= deduct_amount
        bot.reply_to(
            message,
            f"✅ تم الخصم بنجاح!\n\n📱 الحساب: `{found_phone}`\n💸 المبلغ المخصوم: {deduct_amount}\n💰 المتبقي: {accounts_data[found_phone]['balance']}\n\n"
            + get_accounts_text(),
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )
      else:
        bot.reply_to(
            message,
            "⚠️ المبلغ المراد خصمه أكبر من الرصيد المتاح في هذا الحساب!",
            reply_markup=get_main_keyboard(),
        )
    else:
      # طريقة بديلة تفاعلية إذا لم يتعرف البوت على الرقم تلقائياً من الصورة بدقة
      bot.reply_to(
          message,
          "⚠️ لم أستطع مطابقة رقم الحساب تلقائياً من الصورة بدقة.\n\n"
          "💡 **نصيحة:** اكتب رقم الحساب والمبلغ في التعليق (Caption) مع الصورة هكذا:\n"
          "`01234567891`\n`500`",
          reply_markup=get_main_keyboard(),
          parse_mode="Markdown",
      )

  except Exception as e:
    bot.reply_to(
        message,
        f"⚠️ حدث خطأ أثناء معالجة الصورة: {str(e)}",
        reply_markup=get_main_keyboard(),
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
  if call.data == "show_list":
    bot.answer_callback_query(call.id, "تم تحديث القائمة")
    bot.edit_message_text(
        get_accounts_text(),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )
  elif call.data == "clear":
    accounts_data.clear()
    bot.answer_callback_query(call.id, "تم مسح القائمة بالكامل")
    bot.edit_message_text(
        get_accounts_text(),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )
  else:
    bot.answer_callback_query(call.id, "قيد التفعيل...")


@server.route("/")
def webhook():
  return "Bot is running!", 200


if __name__ == "__main__":
  import threading

  def run_bot():
    bot.infinity_polling(none_stop=True)

  t = threading.Thread(target=run_bot)
  t.start()

  port = int(os.environ.get("PORT", 5000))
  server.run(host="0.0.0.0", port=port)
