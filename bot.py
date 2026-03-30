from telebot import TeleBot, types
import requests
import zipfile
import io
import traceback

API_TOKEN = '8657791091:AAFKku0PmV9KTwdSWsf17DW--6zSqf05s7s'
bot = TeleBot(API_TOKEN)

START_MESSAGE = "🌟 مرحبًا بك! أرسل لي أي فيديو MP4 وسأحوّله إلى صور مذهلة لك كألبومات. 🎬✨"

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
                bot.reply_to(message, "❌ أرسل فيديو فقط!")
                return
            file_id = message.document.file_id
            file_size = message.document.file_size

        if file_size > 50*1024*1024:
            bot.reply_to(message, "❌ الفيديو أكبر من 50 ميجا، لا يمكن المعالجة.")
            return

        status_msg = bot.reply_to(message, "⏳ استلمت الفيديو! جاري تحويله إلى صور رائعة... 🌈")

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
                bot.edit_message_text("❌ لم يتم استخراج أي صور من الفيديو. 😔", chat_id=message.chat.id, message_id=status_msg.message_id)
                return

            album = []
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
                        bot.edit_message_text(f"❌ خطأ أثناء إرسال الألبوم: {e}", chat_id=message.chat.id, message_id=status_msg.message_id)
                    album = []
                    bot.edit_message_text(f"📤 جاري إرسال الصور... ({idx}/{len(images)}) 🌟", chat_id=message.chat.id, message_id=status_msg.message_id)

        bot.edit_message_text("✅ تم إرسال جميع الصور! استمتع بمجموعتك الرائعة! 🎉", chat_id=message.chat.id, message_id=status_msg.message_id)

    except requests.exceptions.RequestException as e:
        bot.reply_to(message, f"❌ خطأ في الاتصال: {e}")
        print(traceback.format_exc())
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ غير متوقع: {e}")
        print(traceback.format_exc())

bot.infinity_polling()
