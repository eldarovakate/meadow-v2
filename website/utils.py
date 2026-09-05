import re

_MONTHS_GENITIVE_RU = [
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]


def parse_price_to_int(price):
    """Extract an integer amount from a free-text price string like '4800 ₽'."""
    if not price:
        return None
    digits = re.sub(r'[^\d]', '', str(price))
    return int(digits) if digits else None


def format_date_ru(d):
    """'1 октября 2026 года' — Django's |date:"E" filter gives nominative month names, wrong for this phrasing."""
    return f"{d.day} {_MONTHS_GENITIVE_RU[d.month - 1]} {d.year} года"


def format_date_ru_short(d):
    """'1 октября' — day + month only, for compact headline use (no year/'года')."""
    return f"{d.day} {_MONTHS_GENITIVE_RU[d.month - 1]}"
