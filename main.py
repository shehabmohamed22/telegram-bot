import os
import telebot
from flask import Flask
from telebot import types

# التوكن الخاص بك
TOKEN = "9129643719:AAHxxMGZmYvXQHIXYFCxUY88nbhWVPn6plQ"
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# تخزين الحسابات والأرصدة
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


# استقبال القائمة النصية ومعالجة عدة حسابات دفعة واحدة
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


# استقبال الصور (الإيصالات)
@bot.message_handler(content_types=["photo"])
def handle_receipt(message):
  bot.reply_to(
      message,
      "🔍 جاري قراءة الإيصال واستخراج الحساب والمبلغ...",
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
