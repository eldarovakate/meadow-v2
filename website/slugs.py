"""Latin-only page slugs.

Cyrillic slugs work, but browsers copy them as percent-encoded garbage
(/catalog/%D1%84%D1%83...), which is ugly to share. Every page slug is
transliterated to Latin on save instead.
"""
from django.utils.text import slugify

_RU_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def latin_slug(value):
    """'футболка-лиса-оранжевая' -> 'futbolka-lisa-oranzhevaya'."""
    text = ''.join(_RU_TO_LAT.get(ch, ch) for ch in str(value).lower())
    return slugify(text)


class LatinSlugMixin:
    """Page mixin: transliterate a non-ASCII slug before Wagtail validates it."""

    def full_clean(self, *args, **kwargs):
        if not self.slug and self.title:
            self.slug = latin_slug(self.title)
        elif self.slug and not self.slug.isascii():
            self.slug = latin_slug(self.slug)
        return super().full_clean(*args, **kwargs)
