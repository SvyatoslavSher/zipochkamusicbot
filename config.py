import os
import logging
import sys
from dotenv import load_dotenv

import static_ffmpeg
static_ffmpeg.add_paths()  # Скачает ffmpeg при первом запуске и добавит в PATH

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- ПРОКСИ ОТКЛЮЧЕНЫ ДЛЯ ХОСТИНГА ---
# Если вы запускаете бота локально и вам нужны прокси, раскомментируйте их.
# На хостинге (в зоне без ограничений) они не нужны.

# TELEGRAM_PROXY = "socks5://incy_5a2f6afb:3c2a4f41029ddb300afb0ec27d6b3650@127.0.0.1:10808"
# YOUTUBE_PROXY = "socks5://127.0.0.1:40000"

TELEGRAM_PROXY = None  # Прямое подключение к Telegram
YOUTUBE_PROXY = None   # Прямое подключение к YouTube

DOWNLOAD_DIR = "downloads"
FFMPEG_LOCATION = r"D:\Programs\ffmpeg-9.0.2-essentials_build\bin"
SEARCH_LIMIT = 10

# COOKIES для обхода ограничения в возрасте
COOKIES_PATH = os.path.join(os.path.dirname(__file__), "cookies.txt")

if not os.path.exists(COOKIES_PATH):
    logger.warning(f"Файл cookies.txt не найден по пути: {COOKIES_PATH}")