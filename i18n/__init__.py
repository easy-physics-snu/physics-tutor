from i18n.catalog import translate
from i18n.locale import DEFAULT_LOCALE, SUPPORTED_LOCALES, get_locale, normalize_locale, set_locale
from i18n.session import reset_learning_session


def t(key: str, locale: str | None = None, **values) -> str:
    """Return a localized string for the active locale."""
    return translate(key, locale=locale or get_locale(), **values)


def lt(korean: str, english: str, locale: str | None = None) -> str:
    """Select between an inline Korean/English translation pair."""
    return english if normalize_locale(locale or get_locale()) == "en" else korean


def ai_language_instruction(locale: str | None = None) -> str:
    """Return an explicit response-language rule for AI prompts."""
    return lt(
        "\n\n중요: 학생에게 보여줄 모든 답변은 한국어로 작성하세요.",
        "\n\nIMPORTANT: Write every response shown to the student in English.",
        locale=locale,
    )


__all__ = [
    "DEFAULT_LOCALE",
    "SUPPORTED_LOCALES",
    "ai_language_instruction",
    "get_locale",
    "lt",
    "normalize_locale",
    "reset_learning_session",
    "set_locale",
    "t",
    "translate",
]
