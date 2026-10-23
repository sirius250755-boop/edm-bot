import os
import time
import random
import schedule
import telebot
from yt_dlp import YoutubeDL

# Токен бота
TOKEN = "8696722181:AAFiYNNvgroYxVmGjpgeaE9oJhZKMzaYe90"

# Юзернейм канала
CHANNEL_USERNAME = "@PulseRoom"

bot = telebot.TeleBot(TOKEN)

# Поисковые запросы на отдельные треки (никаких часовых альбомов!)
SEARCH_QUERIES = [
    "underground drum and bass track audio",
    "jump up dnb original track",
    "classic trance club track audio",
    "psytrance original track audio",
    "minimal techno track high quality",
    "acid techno club track audio",
    "deep house original track audio",
    "hard techno club track audio",
    "tech house original mix track"
]

PUBLISHED_FILE = "published_tracks.txt"

def load_published():
    if not os.path.exists(PUBLISHED_FILE):
        return set()
    with open(PUBLISHED_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_published(video_id):
    with open(PUBLISHED_FILE, "a") as f:
        f.write(f"{video_id}\n")

def get_smart_hashtags(title):
    t = title.lower()
    tags = ["#edm", "#underground", "#electronicmusic", "#release2026"]
    
    if "dnb" in t or "drum" in t or "bass" in t or "jump up" in t:
        tags.extend(["#drumnbass", "#dnb", "#jumpup", "#dnbnation"])
    if "trance" in t:
        tags.extend(["#trance", "#trancefamily", "#trancemusic", "#psytrance"])
    if "techno" in t or "acid" in t:
        tags.extend(["#techno", "#acidtechno", "#minimaltechno", "#technomusic"])
    if "house" in t or "deep" in t or "tech house" in t:
        tags.extend(["#housemusic", "#deephouse", "#techhouse", "#house"])
    if "hard" in t:
        tags.extend(["#hardtechno", "#rave", "#hardmusic"])
        
    return " ".join(list(set(tags)))

def post_single_track():
    published_ids = load_published()
    base_query = random.choice(SEARCH_QUERIES)
    query = f"ytsearch15:{base_query}" # Ищем сразу 15 вариантов, чтобы точно выбрать короткий трек

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'writethumbnail': True,
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 60,
        'extractor_retries': 5,
    }

    for attempt in range(1, 4):
        try:
            os.makedirs('downloads', exist_ok=True)
            time.sleep(2)
            
            with YoutubeDL(ydl_opts) as ydl:
                print(f"🔍 Ищу короткий трек (попытка {attempt}/3)...")
                info = ydl.extract_info(query, download=False)
                
                if 'entries' not in info or len(info['entries']) == 0:
                    continue

                # Жесткий фильтр в Python: отсекаем всё длиннее 10 минут (600 секунд) и уже опубликованное
                valid_entries = []
                for e in info['entries']:
                    if not e or e.get('id') in published_ids:
                        continue
                    duration = e.get('duration', 0)
                    title_lower = e.get('title', '').lower()
                    
                    # Проверяем, чтобы в названии не было слов "album", "mix", "full" и длительность была до 10 минут
                    if duration and duration <= 600 and 'mix' not in title_lower and 'album' not in title_lower and 'full' not in title_lower:
                        valid_entries.append(e)

                # Если идеальных не нашлось, берем любые короче 10 минут
                if not valid_entries:
                    for e in info['entries']:
                        if e and e.get('id') not in published_ids and e.get('duration', 0) <= 600:
                            valid_entries.append(e)

                if not valid_entries:
                    print("⚠️ Не найдено подходящих коротких треков, повторяю поиск...")
                    continue

                track_info = random.choice(valid_entries)

                audio_id = track_info.get('id')
                title = track_info.get('title', 'EDM Track')
                uploader = track_info.get('uploader', 'EDM Artist')
                webpage_url = track_info.get('webpage_url')

                print(f"📥 Скачиваю трек: {uploader} - {title}")
                ydl.download([webpage_url])

                audio_path = None
                for ext in ['.mp3', '.m4a', '.webm', '.opus', '.wav']:
                    potential_path = f"downloads/{audio_id}{ext}"
                    if os.path.exists(potential_path):
                        audio_path = potential_path
                        break

                if not audio_path or os.path.getsize(audio_path) < 50000:
                    print("⚠️ Файл поврежден или слишком мал, пробую снова...")
                    continue
                
                thumb_path = None
                for ext in ['.jpg', '.webp', '.png', '.jpeg']:
                    potential_path = f"downloads/{audio_id}{ext}"
                    if os.path.exists(potential_path):
                        thumb_path = potential_path
                        break

                hashtags_only = get_smart_hashtags(title + " " + uploader)

                # 1. Отправляем картинку с чистыми тегами
                if thumb_path and os.path.exists(thumb_path):
                    with open(thumb_path, 'rb') as thumb_file:
                        bot.send_photo(
                            chat_id=CHANNEL_USERNAME,
                            photo=thumb_file,
                            caption=hashtags_only,
                            parse_mode="Markdown"
                        )
                    time.sleep(2)

                # 2. Отправляем аудиоплеер
                with open(audio_path, 'rb') as audio_file:
                    bot.send_audio(
                        chat_id=CHANNEL_USERNAME,
                        audio=audio_file,
                        title=title[:60],
                        performer=uploader[:50],
                        parse_mode="Markdown"
                    )

                save_published(audio_id)
                print(f"✅ Успешно выложено в канал: {uploader} - {title}")

                # Очистка
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if thumb_path and os.path.exists(thumb_path):
                    os.remove(thumb_path)
                    
                return True

        except Exception as e:
            print(f"⚠️ Ошибка сети (попытка {attempt}/3): {e}")
            time.sleep(5)
            
    return False

def auto_post_batch():
    print("🚀 Запуск плановой отправки трека...")
    post_single_track()

# Публикация ровно КАЖДЫЕ 2 ЧАСА
schedule.every(2).hours.do(auto_post_batch)

if __name__ == '__main__':
    print("🚀 Бот PulseRoom запущен (только короткие треки, каждые 2 часа)!")
    auto_post_batch()
    
    while True:
        schedule.run_pending()
        time.sleep(60)