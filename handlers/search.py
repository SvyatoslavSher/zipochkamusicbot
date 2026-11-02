import asyncio
import os
import time

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import logger
from services.search import (
    search_tracks,
    get_platform_links,
    search_youtube_regular,
)
from services.downloader import (
    download_audio,
    get_mp3_path,
    get_thumb_path,
    embed_cover,
    cleanup,
    purge_downloads,
    AgeRestrictedError,  # <-- Импортируем исключение для возрастных видео
)

router = Router()

# Хранилища в памяти
_user_results: dict[int, list[dict]] = {}
_user_queries: dict[int, str] = {}

# Очистка папки загрузок при старте
purge_downloads()

BOT_LINK = "https://t.me/zipochkamusic_bot"
BOT_LINK_TEXT = "Бот для поиска музыки @zipochkamusic_bot"
USER_ERROR = "Не получилось найти трек, пожалуйста попробуйте позже"
AGE_ERROR = "🚫 Этот трек имеет возрастное ограничение на YouTube. К сожалению, бот не может его скачать. Попробуйте найти другой трек или версию."


def _user_info(user) -> str:
    """Возвращает удобную для логов строку с информацией о пользователе."""
    username = f"@{user.username}" if user.username else "no_username"
    return f"{username} (ID: {user.id})"


@router.message(F.text & ~F.text.startswith("/"))
async def handle_search(message: Message):
    user_id = message.from_user.id
    query = message.text.strip()

    if len(query) < 2:
        await message.answer(USER_ERROR)
        return

    logger.info(f"ПОИСК | {_user_info(message.from_user)} | запрос: {query}")

    # 1. Отправляем переходное сообщение "Ищу..."
    status_msg = await message.answer("🔍 Ищу...")

    try:
        tracks = search_tracks(query)
    except Exception as e:
        logger.error(f"ОШИБКА ПОИСКА | {_user_info(message.from_user)} | {query} | {e}")
        await status_msg.edit_text(USER_ERROR)
        return

    _user_queries[user_id] = query

    # 2. Удаляем сообщение "Ищу..." и показываем результат
    await status_msg.delete()

    if not tracks:
        logger.warning(f"НЕ НАЙДЕНО | {_user_info(message.from_user)} | {query}")
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🔎 Искать на YouTube",
            callback_data="search_yt_regular"
        )
        await message.answer(
            "В YouTube Music ничего не найдено. Попробовать поискать на обычном YouTube?",
            reply_markup=builder.as_markup()
        )
        return

    # Ограничиваем до 10 треков
    tracks = tracks[:10]
    _user_results[user_id] = tracks

    builder = InlineKeyboardBuilder()
    for i, t in enumerate(tracks):
        title = t["title"] or "Без названия"
        artists = t["artists"] or "Неизвестный исполнитель"
        builder.button(text=f"{i + 1}. {title} — {artists}", callback_data=f"pick:{i}")

    builder.button(
        text="🔎 Искать на YouTube",
        callback_data="search_yt_regular"
    )
    builder.adjust(1)

    await message.answer("🎵 Выбери трек:", reply_markup=builder.as_markup())


@router.callback_query(F.data == "search_yt_regular")
async def handle_yt_regular_search(callback: CallbackQuery):
    user_id = callback.from_user.id
    query = _user_queries.get(user_id)

    if not query:
        await callback.answer(USER_ERROR, show_alert=True)
        return

    logger.info(f"ПОИСК (обычный YouTube) | {_user_info(callback.from_user)} | запрос: {query}")

    # 1. Меняем текст списка на "Ищу на YouTube..."
    await callback.message.edit_text("🔎 Ищу на обычном YouTube...")
    await callback.answer()

    try:
        tracks = search_youtube_regular(query)
    except Exception as e:
        logger.error(f"ОШИБКА ПОИСКА (обычный YouTube) | {_user_info(callback.from_user)} | {query} | {e}")
        await callback.message.edit_text(USER_ERROR)
        return

    if not tracks:
        logger.warning(f"НЕ НАЙДЕНО (обычный YouTube) | {_user_info(callback.from_user)} | {query}")
        await callback.message.edit_text(USER_ERROR)
        return

    _user_results[user_id] = tracks

    # 2. Показываем новый список (заменяя текст "Ищу...")
    builder = InlineKeyboardBuilder()
    for i, t in enumerate(tracks):
        title = t["title"] or "Без названия"
        artists = t["artists"] or "Неизвестный канал"
        builder.button(text=f"{i + 1}. {title} — {artists}", callback_data=f"pick:{i}")
    builder.adjust(1)

    await callback.message.edit_text(
        "🎵 Найдено на обычном YouTube. Выбери трек:",
        reply_markup=builder.as_markup()
    )


def _build_caption(links: dict) -> str:
    """Формирует подпись: ссылка на бота + список площадок."""
    lines = [f'🎧 <a href="{BOT_LINK}">{BOT_LINK_TEXT}</a>', ""]

    if links:
        lines.append("Трек на других площадках:")
        for name, url in links.items():
            if url:
                lines.append(f"• <a href='{url}'>{name}</a>")

    return "\n".join(lines)


@router.callback_query(F.data.startswith("pick:"))
async def handle_pick(callback: CallbackQuery):
    user_id = callback.from_user.id
    index = int(callback.data.split(":")[1])
    tracks = _user_results.get(user_id, [])

    if index >= len(tracks):
        await callback.answer(USER_ERROR, show_alert=True)
        return

    track = tracks[index]
    title = track["title"] or "Без названия"
    artists = track["artists"] or "Неизвестный исполнитель"
    video_id = track["video_id"]

    await callback.answer()

    start_time = time.time()
    user_str = _user_info(callback.from_user)
    logger.info(f"ЗАГРУЗКА | {user_str} | {artists} - {title} | video_id={video_id}")

    # 1. Удаляем список треков и показываем "Загружаю..."
    try:
        await callback.message.delete()
        status_msg = await callback.message.answer(f"⏳ Загружаю: {title}...")
    except Exception as e:
        logger.warning(f"Не удалось изменить сообщение на 'Загружаю': {e}")
        status_msg = await callback.message.answer(f"⏳ Загружаю: {title}...")

    file_id = None
    try:
        loop = asyncio.get_running_loop()

        # 2. Скачиваем аудио
        file_id = await loop.run_in_executor(None, download_audio, video_id)
        mp3_path = get_mp3_path(file_id)
        thumb_path = get_thumb_path(file_id)

        # 3. Встраиваем обложку
        jpeg_thumb_path = None
        if thumb_path:
            jpeg_thumb_path = await loop.run_in_executor(
                None, embed_cover, mp3_path, thumb_path
            )

        # 4. Ищем ссылки на площадки
        platform_links = await loop.run_in_executor(
            None, get_platform_links, artists, title
        )
        yt_music_url = f"https://music.youtube.com/watch?v={video_id}"
        all_links = {"YouTube Music": yt_music_url, **platform_links}
        caption = _build_caption(all_links)

        # 5. Удаляем "Загружаю..." и отправляем аудио
        await status_msg.delete()

        audio_file = FSInputFile(mp3_path, filename=f"{artists} - {title}.mp3")
        thumbnail_file = None
        if jpeg_thumb_path and os.path.exists(jpeg_thumb_path):
            thumbnail_file = FSInputFile(jpeg_thumb_path)

        await callback.message.answer_audio(
            audio=audio_file,
            thumbnail=thumbnail_file,
            title=title,
            performer=artists,
            caption=caption,
            parse_mode="HTML",
        )

        # Логируем успех
        elapsed = round(time.time() - start_time, 2)
        logger.info(f"УСПЕХ | {user_str} | {artists} - {title} | {elapsed} сек.")

    except AgeRestrictedError:
        # Обработка возрастного ограничения
        logger.warning(f"ВОЗРАСТНОЕ ОГРАНИЧЕНИЕ | {user_str} | {artists} - {title}")
        try:
            await status_msg.delete()
        except:
            pass
        await callback.message.answer(AGE_ERROR)
    except Exception as e:
        logger.error(f"ОШИБКА ЗАГРУЗКИ | {user_str} | {artists} - {title} | {e}")
        # Удаляем "Загружаю..." и показываем ошибку
        try:
            await status_msg.delete()
        except:
            pass
        await callback.message.answer(USER_ERROR)
    finally:
        if file_id:
            cleanup(file_id)