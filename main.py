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


# استقبال الصور (الإيصالات) وتطبيق الخصم الاحترافي
@bot.message_handler(content_types=["photo"])
def handle_receipt(message):
  global accounts_data
  bot.reply_to(
      message,
      "🔍 جاري تحليل الإيصال والخصم تلقائياً...",
      reply_markup=get_main_keyboard(),
  )

  try:
    fileID = message.photo[-1].file_id
    file_info = bot.get_file(fileID)
    downloaded_file = bot.download_file(file_info.file_path)

    image_path = "temp_receipt.jpg"
    with open(image_path, "wb") as new_file:
      new_file.write(downloaded_file)

    extracted_text = ""
    try:
      import pytesseract
      from PIL import Image

      extracted_text = pytesseract.image_to_string(Image.open(image_path))
    except Exception:
      pass

    caption = message.caption if message.caption else ""
    full_search_text = extracted_text + " " + caption

    # البحث عن رقم الحساب المسجل المذكور داخل النص أو الصورة
    matched_phone = None
    for phone in accounts_data.keys():
      if phone in full_search_text:
        matched_phone = phone
        break

    # استخراج الأرقام والمبالغ المالية من النص
    numbers = re.findall(
        r"\d+", full_search_text.replace(",", "")
    )  # إزالة الفواصل لتسهيل القراءة

    if matched_phone and len(numbers) >= 1:
      # اختيار المبلغ المناسب (افتراض أن المبلغ هو الأكبر أو آخر رقم ظاهر)
      # سنبحث عن أرقام تمثل مبالغ مالية (عادة أكبر من 10 لتجنب الأرقام الصغيرة)
      valid_amounts = [
          float(n) for n in numbers if float(n) > 10 and n != matched_phone
      ]

      if valid_amounts:
        deduct_amount = valid_amounts[-1]  # أخذ آخر مبلغ محول ظاهر في الإيصال

        if accounts_data[matched_phone]["balance"] >= deduct_amount:
          accounts_data[matched_phone]["balance"] -= deduct_amount
          name = accounts_data[matched_phone]["name"]
          new_balance = accounts_data[matched_phone]["balance"]

          bot.reply_to(
              message,
              f"✅ تم خصم {deduct_amount} من ({matched_phone}) {name}\n"
              f"💰 المبلغ الجديد: {new_balance}\n\n" + get_accounts_text(),
              reply_markup=get_main_keyboard(),
              parse_mode="Markdown",
          )
        else:
          bot.reply_to(
              message,
              "⚠️ عذراً، المبلغ المراد خصمه أكبر من الرصيد المتاح لهذا الحساب!",
              reply_markup=get_main_keyboard(),
          )
      else:
        bot.reply_to(
            message,
            "⚠️ لم يتم التعرف على مبلغ التحويل بوضوح من الصورة.",
            reply_markup=get_main_keyboard(),
        )
    else:
      bot.reply_to(
          message,
          "⚠️ لم أتمكن من مطابقة رقم الحساب تلقائياً.\n"
          "💡 يرجى كتابة رقم الحساب والمبلغ في تعليق الصورة هكذا:\n"
          "`01234567891`\n`500`",
          reply_markup=get_main_keyboard(),
          parse_mode="Markdown",
      )

  except Exception as e:
    bot.reply_to(
        message,
        f"⚠️ حدث خطأ أثناء معالجة الإيصال: {str(e)}",
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
