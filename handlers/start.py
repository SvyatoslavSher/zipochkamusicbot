from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from locales import get_text
from storage.user_lang import get_lang

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(get_text(lang, "start"), parse_mode="HTML")