import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN, TELEGRAM_PROXY, logger
from handlers import start, search, language

def build_bot() -> Bot:
    # Если прокси нет, создаем сессию без него
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