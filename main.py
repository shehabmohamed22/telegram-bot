import os
import telebot
from flask import Flask
from telebot import types

TOKEN = "9108440921:AAE1CBG23VAUkbdweShWBsl4k7lnDk8A_Sk"  # أو التوكن الجديد لو أنشأت بوت جديد
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# قائمة فارغة لتخزين الأرقام والمبالغ التي ستدخلها أنت لاحقاً
accounts_data = {}


def get_accounts_text():
  if not accounts_data:
    return (
        "📊 **Limits / القائمة الحالية:**\n\n"
        "القائمة فارغة حالياً.\nأضف الحسابات والمبالغ للبدء."
    )

  text = "📊 **Limits / القائمة الحالية:**\n\n"
  for phone, info in accounts_data.items():
    text += f"`{phone}`\n💰 {info['balance']}\n👤 {info['name']}\n\n"
  return text


# لوحة الأزرار التفاعلية نفس الشكل المطلوب
def get_main_keyboard():
  markup = types.InlineKeyboardMarkup(row_width=2)
  btn_deduct = types.InlineKeyboardButton("➖ خصم", callback_data="deduct")
  btn_add = types.InlineKeyboardButton("➕ إضافة مبلغ", callback_data="add")
  btn_list = types.InlineKeyboardButton("📋 عرض القائمة", callback_data="show_list")
  btn_undo = types.InlineKeyboardButton(
      "↩️ تراجع عن الأخير", callback_data="undo"
  )
  btn_clear = types.InlineKeyboardButton("🗑️ مسح الكل", callback_data="clear")
  btn_extra = types.InlineKeyboardButton("📁 خيارات إضافية", callback_data="extra")

  markup.add(btn_deduct, btn_add, btn_list, btn_undo, btn_clear, btn_extra)
  return markup


@bot.message_handler(commands=["start", "limits", "help"])
def send_welcome(message):
  bot.send_message(
      message.chat.id,
      get_accounts_text(),
      reply_markup=get_main_keyboard(),
      parse_mode="Markdown",
  )


# التعامل مع ضغطات الأزرار
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
    bot.answer_callback_query(call.id, "هذا الزر قيد الربط!")


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
