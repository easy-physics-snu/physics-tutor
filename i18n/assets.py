"""Select the English versions of learning images without altering originals."""
from pathlib import PurePosixPath

from i18n.locale import get_locale, normalize_locale


LOCALIZED_IMAGES = frozenset({
    "explain_2.png",
    "explain_4.png",
    "explain_5.png",
    "new_review_1.png",
    "find_tab_guide.png",
    "find_answer_guide.png",
})


def localized_image_path(path: str, locale: str | None = None) -> str:
    """Resolve known learning assets; language-neutral images keep their path."""
    image = PurePosixPath(path)
    selected_locale = get_locale() if locale is None else normalize_locale(locale)
    if (selected_locale == "en" and image.parent == PurePosixPath("src/images")
            and image.name in LOCALIZED_IMAGES):
        return str(image.parent / "en" / image.name)
    return path
