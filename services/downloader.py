import os
import glob
import uuid
import subprocess
from yt_dlp import YoutubeDL

from config import DOWNLOAD_DIR, YOUTUBE_PROXY, FFMPEG_LOCATION, COOKIES_PATH, logger

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class AgeRestrictedError(Exception):
    """Исключение для видео с возрастным ограничением."""
    pass


def download_audio(video_id: str) -> str:
    """
    Скачивает аудио и обложку. Возвращает file_id.
    Если видео имеет возрастное ограничение, выбрасывает AgeRestrictedError.
    """
    file_id = uuid.uuid4().hex
    out_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")
    url = f"https://music.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "format": "bestaudio/best",
        "proxy": YOUTUBE_PROXY,
        "writethumbnail": True,
        "cookiefile": COOKIES_PATH,
        # web_creator лучше всего работает с cookies для обхода возрастных ограничений.
        # tv_embedded и default добавлены как запасные варианты.
        "extractor_args": {"youtube": {"player_client": ["web_creator", "tv_embedded", "default"]}},
        "remote_components": "ejs:github",  # для n challenge (нужен deno)
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
        ],
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        error_msg = str(e)
        # Проверяем, связана ли ошибка с возрастом
        if "Sign in to confirm your age" in error_msg or "age-restricted" in error_msg.lower():
            raise AgeRestrictedError("Видео имеет возрастное ограничение")
        raise e  # Пробрасываем другие ошибки дальше

    mp3_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")
    if not os.path.exists(mp3_path):
        raise RuntimeError("MP3 не был создан после загрузки")
    
    # Логируем размер файла
    size_mb = round(os.path.getsize(mp3_path) / (1024 * 1024), 2)
    logger.info(f"Файл скачан: {size_mb} МБ")
    
    return file_id


def get_mp3_path(file_id: str) -> str:
    """Возвращает путь к MP3-файлу по его file_id."""
    return os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")


def get_thumb_path(file_id: str) -> str | None:
    """Возвращает путь к скачанной обложке, если она есть."""
    for ext in ("webp", "jpg", "jpeg", "png"):
        candidate = os.path.join(DOWNLOAD_DIR, f"{file_id}.{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def embed_cover(mp3_path: str, thumb_path: str) -> str | None:
    """
    Встраивает обложку в MP3 через цепочку WebP -> PNG -> JPEG.
    Возвращает путь к JPEG-обложке (для Telegram) или None.
    """
    if not thumb_path or not os.path.exists(thumb_path):
        return None

    ffmpeg_exe = os.path.join(FFMPEG_LOCATION, "ffmpeg.exe")
    base = os.path.splitext(mp3_path)[0]
    png_path = base + "_cover.png"
    jpg_path = base + "_cover.jpg"

    # Шаг 1: WebP -> PNG
    r1 = subprocess.run([
        ffmpeg_exe, "-y", "-i", thumb_path, png_path
    ], capture_output=True, text=True)
    if r1.returncode != 0:
        return None

    # Шаг 2: PNG -> JPEG (mjpeg)
    r2 = subprocess.run([
        ffmpeg_exe, "-y", "-i", png_path,
        "-c:v", "mjpeg", "-q:v", "2", jpg_path
    ], capture_output=True, text=True)
    if r2.returncode != 0:
        return None

    # Шаг 3: Встраиваем JPEG в MP3
    tmp_mp3 = base + "_with_cover.mp3"
    r3 = subprocess.run([
        ffmpeg_exe, "-y",
        "-i", mp3_path,
        "-i", jpg_path,
        "-map", "0:a",
        "-map", "1:v",
        "-c:a", "copy",
        "-c:v", "mjpeg",
        "-id3v2_version", "3",
        "-metadata:s:v", "title=Album cover",
        "-metadata:s:v", "comment=Cover (front)",
        tmp_mp3,
    ], capture_output=True, text=True)
    if r3.returncode != 0:
        return None

    os.replace(tmp_mp3, mp3_path)

    # Удаляем только PNG, JPEG оставляем для Telegram
    if os.path.exists(png_path):
        os.remove(png_path)

    return jpg_path


def cleanup(file_id: str) -> None:
    """
    Удаляет все файлы, связанные с file_id:
    основной mp3, обложки, промежуточные файлы.
    """
    pattern = os.path.join(DOWNLOAD_DIR, f"*{file_id}*")
    for path in glob.glob(pattern):
        try:
            os.remove(path)
        except OSError:
            pass


def purge_downloads() -> None:
    """Удаляет всё содержимое DOWNLOAD_DIR при старте бота."""
    for path in glob.glob(os.path.join(DOWNLOAD_DIR, "*")):
        try:
            os.remove(path)
        except OSError:
            pass