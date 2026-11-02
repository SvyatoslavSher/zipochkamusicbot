from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from locales import get_text
from storage.user_lang import get_lang, set_lang

router = Router()


@router.message(Command("lang"))
async def cmd_lang(message: Message):
    lang = get_lang(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.button(text="🇷🇺 Русский", callback_data="lang:ru")
    builder.button(text="🇬🇧 English", callback_data="lang:en")
    builder.adjust(2)
    await message.answer(
        get_text(lang, "choose_language"),
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("lang:"))
async def handle_lang_choice(callback: CallbackQuery):
    new_lang = callback.data.split(":")[1]
    set_lang(callback.from_user.id, new_lang)
    await callback.message.edit_text(get_text(new_lang, "language_set"))
    await callback.answer()