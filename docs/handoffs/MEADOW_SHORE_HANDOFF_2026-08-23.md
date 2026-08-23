# Meadow Shore — Handoff snapshot, 2026-08-23

Исторический снимок состояния проекта на 2026-08-23. **Не редактировать задним числом** — это фиксированная точка во времени, не текущий статус. Актуальное состояние всегда в [../PROJECT_STATE.md](../PROJECT_STATE.md).

Полный технический журнал этого захода на редизайн (архитектурные решения, находки, полный список изменённых файлов) — [../site-redesign-progress.md](../site-redesign-progress.md); этот handoff — его сжатая выжимка для быстрой передачи контекста.

---

## Бренд

- Meadow Shore — designer clothing brand, тактильный характер, editorial, не cottagecore/eco-shop/сувенирная лавка.
- Публичная коммуникация — русский язык, минимум англицизмов.
- Первая коллекция: **«Лесные жители»** (единственное публичное имя).
- Сайт = интернет-магазин + визуальный архив бренда (система «Наблюдений»).

## Стек

Django 4.2 + Wagtail 5.2, `HomePage` через StreamField, общий `static/css/style.css` и `static/js/main.js`, переиспользуемые `product_card.html`/`product_carousel.html`.

## Production state на эту дату

| | |
|---|---|
| URL | https://meadowshore.ru/ |
| Commit | `0465819` — "Redesign Meadow Shore homepage" |
| Django check | `System check identified no issues (0 silenced).` |
| Migrations | `home.0010`, `home.0011`, `home.0012`, `website.0007_order_orderitem` |

## Выполнено: HOME-01 – HOME-04

- **GLOBAL-01** — адаптивная шапка (mobile/tablet до 1023px, desktop с 1024px), исправлен mobile drawer, Hero CTA использует Wagtail URL.
- **HOME-01** — новый editorial-Hero. Тексты: eyebrow `КОЛЛЕКЦИЯ 01 · ЛЕСНЫЕ ЖИТЕЛИ`, H1 `Для нас лес — место, куда мы приходим. Для них — дом.`, subheadline `Первая коллекция одежды Meadow Shore посвящена тем, кто остаётся в лесу после того, как мы уходим.`, CTA `Смотреть коллекцию` → `/catalog/`.
- **HOME-02** — новая подача товаров («Первая коллекция»). Eyebrow `ПЕРВАЯ КОЛЛЕКЦИЯ`, H2 `Лесные жители`, CTA `Смотреть всю коллекцию →`. Карточки homepage: нет «Добавить в корзину», нет «Смотреть вещь», нет discount badge, кликабельны фото и название, карточка заканчивается ценой. Каталог визуально не изменён.
- **HOME-03** — «О коллекции». Eyebrow `О КОЛЛЕКЦИИ`, H2 `Лесные жители`, три абзаца истории коллекции (см. PROJECT_STATE.md за полным текстом).
- **HOME-04** — новый Wagtail block `ObservationSectionBlock` (eyebrow/title/body/image/caption). Первое наблюдение: `НАБЛЮДЕНИЕ № 01` / `Певчая птица`. CTA в Observation отсутствует принципиально.

## Deployment

Автодеплой через `.github/workflows/deploy.yml` при push в `main`. Подробности — [../DEPLOYMENT.md](../DEPLOYMENT.md).

## Pending: ЮKassa

Интеграция начата, но не закончена. Локальные изменения в working tree (`website/payments.py`, `website/models.py`, `website/views.py`, `website/urls.py`, `website/admin.py`, миграция `0008_order_payment_id`, `.env.example`, `requirements.txt`, `meadowshore/settings/base.py`) сознательно не входят в release `0465819`.

## Следующие задачи

1. Завершить ЮKassa (payment flow end-to-end, webhook/callback, статус заказа, ошибки/отмена) → отдельный commit → отдельный production release.
2. HOME-05 — Материалы.
3. HOME-06 — съёмка коллекции.
4. HOME-07 — Архив природы.
5. HOME-08 — О Meadow Shore.
6. HOME-09 — письма Meadow Shore.
7. HOME-10 — footer.
8. HOME-11 — responsive/accessibility/performance/final QA.
