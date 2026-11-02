from locales import ru, en

DEFAULT_LANG = "ru"
SUPPORTED = {"ru": ru.TEXTS, "en": en.TEXTS}


def get_text(lang: str, key: str, **kwargs) -> str:
    """
    Возвращает текст по ключу для указанного языка.
    Если ключа нет — падает обратно на DEFAULT_LANG.
    Поддерживает .format(**kwargs).
    """
    texts = SUPPORTED.get(lang) or SUPPORTED[DEFAULT_LANG]
    template = texts.get(key) or SUPPORTED[DEFAULT_LANG].get(key, key)
    return template.format(**kwargs) if kwargs else template


def is_supported(lang: str) -> bool:
    return lang in SUPPORTED