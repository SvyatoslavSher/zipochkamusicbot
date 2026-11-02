from locales import DEFAULT_LANG

_user_langs: dict[int, str] = {}


def get_lang(user_id: int) -> str:
    return _user_langs.get(user_id, DEFAULT_LANG)


def set_lang(user_id: int, lang: str) -> None:
    _user_langs[user_id] = lang