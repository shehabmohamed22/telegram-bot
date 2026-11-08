import os
import telebot
from flask import Flask

TOKEN = "9108440921:AAE1CBG23VAUkbdweShWBsl4k7lnDk8A_Sk"
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
  bot.reply_to(message, "أهلاً بك! بوت إدارة الحسابات والإيصالات يعمل الآن 24/7.")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
  bot.reply_to(message, f"تم استلام رسالتك: {message.text}")


@server.route("/")
def webhook():
  return "Bot is running!", 200


if __name__ == "__main__":
  # تشغيل البوت مع الـ Web server عشان Render ما يقفلوش
  import threading

  def run_bot():
    bot.infinity_polling(none_stop=True)

  t = threading.Thread(target=run_bot)
  t.start()

  port = int(os.environ.get("PORT", 5000))
  server.run(host="0.0.0.0", port=port)
