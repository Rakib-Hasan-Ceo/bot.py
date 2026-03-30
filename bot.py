import telebot
from telebot import types
import requests
import zipfile
import io
import traceback
import threading
import os
from flask import Flask

# আপনার টেলিগ্রাম বটের টোকেন এখানে দিন
API_TOKEN = 'এখানে_আপনার_টোকেন_দিন'
bot = telebot.TeleBot(API_TOKEN)

# Render এর জন্য ডামি ওয়েব সার্ভার
app = Flask(__name__)
@app.route('/')
def index():
    return "Bot is running successfully!"

# বটের স্টার্ট মেসেজ
START_MESSAGE = "🌟 স্বাগতম! আমাকে যেকোনো MP4 ভিডিও পাঠান আর আমি সেটিকে সুন্দর ছবির অ্যালবামে রূপান্তর করে দেব। 🎬✨"

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, START_MESSAGE)

@bot.message_handler(content_types=['video', 'document'])
def handle_video(message):
    try:
        file_id = None
        file_size = 0
        
        if message.content_type == 'video':
            file_id = message.video.file_id
            file_size = message.video.file_size
        elif message.content_type == 'document':
            if not message.document.mime_type.startswith("video/"):
                bot.reply_to(message, "❌ দয়া করে শুধুমাত্র ভিডিও পাঠান!")
                return
            file_id = message.document.file_id
            file_size = message.document.file_size

        if file_size > 50 * 1024 * 1024:
            bot.reply_to(message, "❌ ভিডিওটির সাইজ ৫০ মেগাবাইটের বেশি, এটি প্রসেস করা সম্ভব নয়।")
            return

        status_msg = bot.reply_to(message, "⏳ আপনার ভিডিও পেয়েছি! ভিডিও থেকে ছবি বের করার কাজ চলছে... 🌈")

        file_info = bot.get_file(file_id)
        telegram_file_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_info.file_path}"

        api_url = "https://mode.giize.com/mode/video.php"
        params = {"url": telegram_file_url}

        response = requests.get(api_url, params=params, timeout=120)
        response.raise_for_status()

        zip_bytes = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_bytes) as zip_file:
            images = sorted([name for name in zip_file.namelist() if name.lower().endswith(".jpg")])
            if not images:
                bot.edit_message_text("❌ ভিডিও থেকে কোনো ছবি আলাদা করা সম্ভব হয়নি। 😔", chat_id=message.chat.id, message_id=status_msg.message_id)
                return

            album =[]
            for idx, img_name in enumerate(images, 1):
                try:
                    with zip_file.open(img_name) as img_file:
                        album.append(types.InputMediaPhoto(img_file.read()))
                except Exception as e:
                    continue

                if len(album) == 6 or idx == len(images):
                    try:
                        bot.send_media_group(message.chat.id, album)
                    except Exception as e:
                        bot.edit_message_text(f"❌ অ্যালবাম পাঠানোর সময় সমস্যা হয়েছে: {e}", chat_id=message.chat.id, message_id=status_msg.message_id)
                    album =[]
                    bot.edit_message_text(f"📤 ছবি পাঠানো হচ্ছে... ({idx}/{len(images)}) 🌟", chat_id=message.chat.id, message_id=status_msg.message_id)

        bot.edit_message_text("✅ সফলভাবে সব ছবি পাঠানো হয়েছে! 🎉", chat_id=message.chat.id, message_id=status_msg.message_id)

    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"❌ নেটওয়ার্ক এরর: {e}")
    except Exception as e:
        bot.reply_to(message, f"❌ একটি অজানা সমস্যা হয়েছে: {e}")

# ওয়েব সার্ভার চালু করার ফাংশন
def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# একসাথে বট এবং ওয়েব সার্ভার চালানো
if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.start()
    print("Bot is polling...")
    bot.infinity_polling()