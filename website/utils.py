import re


def parse_price_to_int(price):
    """Extract an integer amount from a free-text price string like '4800 ₽'."""
    if not price:
        return None
    digits = re.sub(r'[^\d]', '', str(price))
    return int(digits) if digits else None
