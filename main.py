import os
import re
import telebot
from flask import Flask
from openai import OpenAI
from telebot import types

TOKEN = "9129643719:AAHxxMGZmYvXQHIXYFCxUY88nbhWVPn6plQ"
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# تم وضع مفتاح OpenAI الخاص بك هنا وجعله جاهزاً للعمل
client = OpenAI(
    api_key=(
        "Sk-proj-G-Abhrx29tSTaHYD03yaKKsd525PXR7EdsO4qDHTotJcXQRC55-b2VY1Ql1TAYdcirTZf_EfvzT3BlbkFJiOFC4fyT7dUNqfvV1WZVZC5gR6zk4LA1eZ6Gxsoks8Ptar2gPMhyifCTDY-ue4-AZMSSSL7hUA"
    )
)

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
      except ValueError:
        i += 1
        continue
      accounts_data[phone] = {"name": name, "balance": balance}
      added_count += 1
      i += 3

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


# قراءة الإيصالات واكتشاف الحساب والمبلغ عبر الذكاء الاصطناعي (GPT-4o)
@bot.message_handler(content_types=["photo"])
def handle_receipt(message):
  global accounts_data
  bot.reply_to(
      message,
      "🤖 جاري تحليل الإيصال بالذكاء الاصطناعي واستخراج البيانات...",
      reply_markup=get_main_keyboard(),
  )

  try:
    fileID = message.photo[-1].file_id
    file_info = bot.get_file(fileID)
    downloaded_file = bot.download_file(file_info.file_path)

    image_path = "temp_receipt.jpg"
    with open(image_path, "wb") as new_file:
      new_file.write(downloaded_file)

    import base64

    def encode_image(image_path):
      with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

    base64_image = encode_image(image_path)
    available_phones = list(accounts_data.keys())

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that extracts financial transaction"
                    " details from receipt images. Given the image and a list"
                    " of valid phone numbers, find which phone number from the"
                    " list appears in the receipt, and extract the transferred"
                    " amount (as a number). Output strictly in format:"
                    " PHONE: <number> | AMOUNT: <number>. If not found, output"
                    " NOT_FOUND."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Here is the list of valid phone numbers to look"
                            f" for: {available_phones}"
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            },
        ],
        max_tokens=100,
    )

    result_text = response.choices[0].message.content.strip()

    if "NOT_FOUND" in result_text:
      bot.reply_to(
          message,
          "⚠️ لم يتمكن الذكاء الاصطناعي من مطابقة رقم الحساب الموجود في القائمة مع هذا الإيصال.",
          reply_markup=get_main_keyboard(),
      )
      return

    phone_match = re.search(r"PHONE:\s*([^\s|]+)", result_text)
    amount_match = re.search(r"AMOUNT:\s*([\d.]+)", result_text)

    if phone_match and amount_match:
      matched_phone = phone_match.group(1).strip()
      deduct_amount = float(amount_match.group(1))

      if matched_phone in accounts_data:
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
              "⚠️ عذراً، المبلغ المطلوب خصمه أكبر من الرصيد المتاح في الحساب!",
              reply_markup=get_main_keyboard(),
          )
      else:
        bot.reply_to(
            message,
            "⚠️ الحساب المستخرج غير موجود في القائمة الحالية.",
            reply_markup=get_main_keyboard(),
        )
    else:
      bot.reply_to(
          message,
          "⚠️ حدث خطأ في تحليل البيانات المستخرجة من الإيصال.",
          reply_markup=get_main_keyboard(),
      )

  except Exception as e:
    bot.reply_to(
        message,
        f"⚠️ حدث خطأ تقني: {str(e)}",
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
