import asyncio
import os
import stat

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN, TELEGRAM_PROXY, FFMPEG_LOCATION, logger
from handlers import start, search, language


def set_ffmpeg_permissions():
    """
    Выставляет права на выполнение для ffmpeg и ffprobe.
    Критически важно для Linux (хостинг), чтобы бот мог запускать эти файлы.
    """
    for filename in ["ffmpeg", "ffprobe"]:
        filepath = os.path.join(FFMPEG_LOCATION, filename)
        if os.path.exists(filepath):
            try:
                # Добавляем права на выполнение (rwxr-xr-x)
                os.chmod(filepath, 0o755)
                logger.info(f"Установлены права на выполнение для {filepath}")
            except Exception as e:
                logger.warning(f"Не удалось установить права для {filepath}: {e}")


def build_bot() -> Bot:
    """Создаёт бота с прокси для Telegram (если он задан)."""
    if TELEGRAM_PROXY:
        session = AiohttpSession(proxy=TELEGRAM_PROXY)
    else:
        session = AiohttpSession()
    return Bot(token=BOT_TOKEN, session=session)


def build_dispatcher() -> Dispatcher:
    """Создаёт диспетчер и подключает все роутеры."""
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(language.router)
    dp.include_router(search.router)
    return dp


async def main():
    # Устанавливаем права для ffmpeg перед запуском бота
    set_ffmpeg_permissions()

    bot = build_bot()
    dp = build_dispatcher()

    # Лог старта
    logger.info("Бот запущен")

    try:
        await dp.start_polling(bot)
    finally:
        # Лог остановки и корректное закрытие сессии
        logger.info("Бот остановлен")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        # Перехватываем Ctrl+C, чтобы блок finally в main() успел выполниться
        pass