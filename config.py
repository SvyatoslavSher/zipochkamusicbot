import os
import sys
import platform
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# --- Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Токен бота ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Определение ОС ---
IS_WINDOWS = platform.system() == "Windows"

# --- Настройки прокси ---
# На Windows (локально) вы используете INCY и WARP.
# На хостинге (Linux) они не нужны, так как сервер находится в зоне без ограничений.
if IS_WINDOWS:
    # Локальные прокси (раскомментируйте, если нужны)
    TELEGRAM_PROXY = "socks5://incy_5a2f6afb:3c2a4f41029ddb300afb0ec27d6b3650@127.0.0.1:10808"
    YOUTUBE_PROXY = "socks5://127.0.0.1:40000"
else:
    # На хостинге прокси не используем
    TELEGRAM_PROXY = None
    YOUTUBE_PROXY = None

# --- Пути к файлам и папкам ---
# На хостинге используем папку /app/data, которая сохраняется при перезапуске.
# На Windows используем локальную папку "downloads".
if not IS_WINDOWS:
    DOWNLOAD_DIR = os.getenv("DATA_DIR", "/app/data/downloads")
else:
    DOWNLOAD_DIR = "downloads"

# --- Путь к ffmpeg ---
# На Windows указываем путь к вашей локальной сборке.
# На Linux (хостинг) используем стандартный путь /usr/bin или None (поиск в PATH).
if IS_WINDOWS:
    FFMPEG_LOCATION = r"D:\Programs\ffmpeg-9.0.2-essentials_build\bin"
else:
    FFMPEG_LOCATION = "/usr/bin"  # или None, если ffmpeg установлен в PATH

# --- Путь к файлу cookies ---
# Файл должен лежать в корне проекта.
COOKIES_PATH = os.path.join(os.path.dirname(__file__), "cookies.txt")

# --- Лимит поиска ---
SEARCH_LIMIT = 10