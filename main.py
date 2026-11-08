import telebot

TOKEN = "9108440921:AAE1CBG23VAUkbdweShWBsl4k7lnDk8A_Sk"
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
  bot.reply_to(message, "أهلاً بك! بوت إدارة الحسابات والإيصالات يعمل الآن بنجاح 24/7.")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
  bot.reply_to(message, f"تم استلام رسالتك: {message.text}")


bot.infinity_polling()

