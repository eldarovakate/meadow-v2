"""Характеристики товара, собранные из уже существующих текстовых полей.

Ничего не выдумываем: каждое значение либо найдено в тексте товара
(fabric_info, care_info, fit_notes), либо берётся из выбранного в админке
значения (цвет, техника нанесения). Не найдено — значит не показываем.
"""
import re

# Общая размерная таблица футболок коллекции (одинакова для всех моделей).
SIZE_CHART = {
    "sizes": ["S", "M", "L", "XL"],
    "rows": [
        ("Российский размер", ["44–46", "46–48", "48–50", "50–52"]),
        ("Полуобхват груди, см", ["63", "65", "67", "69"]),
        ("Длина изделия, см", ["73", "74", "76", "79"]),
        ("Длина рукава, см", ["26", "27", "28", "30"]),
    ],
    "how_to": [
        "Ширина изделия — от подмышки до подмышки",
        "Ширина плеч — от одного края плеча до другого",
        "Длина изделия — от верхней точки плеча до нижнего края",
        "Рукав — от шва верхней точки рукава до нижнего края",
    ],
    "tolerance": "Допустимые отклонения ±2 см.",
    "intro": "Измерьте свою вещь из гардероба и сверьте с таблицей. "
             "Остались сомнения — напишите нам, сообщив рост и вес.",
}

_COMPOSITION_RE = re.compile(r"\d+\s*%\s*[а-яё]+(?:\s*,\s*\d+\s*%\s*[а-яё]+)*", re.IGNORECASE)
_DENSITY_RE = re.compile(r"(\d+)\s*г/м", re.IGNORECASE)
_FABRIC_RE = re.compile(r"(футер[^.,;\n]*)", re.IGNORECASE)


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def split_lines(text):
    """Строки текстового поля без пустых."""
    return [_clean(line) for line in (text or "").splitlines() if _clean(line)]


def _capitalize(text):
    return text[:1].upper() + text[1:] if text else text


def parse_composition(fabric_info):
    match = _COMPOSITION_RE.search(fabric_info or "")
    return _clean(match.group(0)) if match else ""


def parse_density(fabric_info):
    match = _DENSITY_RE.search(fabric_info or "")
    return f"{match.group(1)} г/м²" if match else ""


def parse_fabric(fabric_info):
    match = _FABRIC_RE.search(fabric_info or "")
    return _clean(match.group(1)) if match else ""


def care_items(care_info):
    """Текст ухода → короткие пункты (по строкам, иначе по предложениям, иначе по запятым)."""
    items = split_lines(care_info)
    if len(items) == 1:
        items = [s for s in re.split(r"(?<=[.!])\s+", items[0]) if s]
    if len(items) == 1:
        items = [s for s in items[0].split(", ") if s]
    return [_capitalize(item.strip().rstrip(".")) for item in items if item.strip(" .")]


def about_paragraphs(fabric_info):
    """Текст «О вещи»: абзацы fabric_info без служебного префикса «Состав:»."""
    return split_lines(fabric_info)
