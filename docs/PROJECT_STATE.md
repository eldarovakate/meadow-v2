# Meadow Shore — текущее состояние проекта

Главный актуальный документ состояния проекта. Если новый разработчик или новая сессия Claude Code открывает проект — начинать нужно отсюда, а не с нового аудита с нуля.

Последнее обновление: 2026-09-30 (только раздел Production; остальные разделы — см. предупреждение ниже).

> ⚠️ **Этот файл устарел.** `git log` на 2026-09-26 показывает минимум 19 коммитов после последнего обновления этого файла — About-страница переделана, на главной появился prelaunch-баннер и launch-блоки, в каталоге фильтры, добавлен флаг `CHECKOUT_ENABLED` (похоже, оплата сейчас может быть выключена — проверить перед тем, как полагаться на раздел «ЮKassa» ниже). Ни один из этих коммитов здесь не отражён. Перед тем как доверять секциям Production/ЮKassa — перечитай `git log` заново.
>
> Отдельно: сессия 2026-09-26 сделала редизайн `/design-lab/home-blocks/` (10 существующих блоков + новая группа 11A–11E Collection Statement Grid, оба этапа с реальными фото бренда). Работа полностью локальная, не в production, не влияет на реальную главную. Подробности — [docs/handoffs/MEADOW_SHORE_HANDOFF_2026-09-26_design-lab.md](handoffs/MEADOW_SHORE_HANDOFF_2026-09-26_design-lab.md).

---

## Production

| | |
|---|---|
| URL | https://meadowshore.ru/ |
| Production commit | `60b21de` — "Pre-launch hardening for checkout, payments and production settings" |
| Дата последнего release | 2026-09-30 |
| Статус | работает; latin slugs + 301 со старых адресов, галерея со стрелками, pre-launch hardening (см. CHANGELOG) |
| Django check | `System check identified no issues (0 silenced).` (2026-09-30, 59 тестов OK) |

Применённые миграции (production, по состоянию на текущий production commit):
- `home.0010_alter_homepage_body`
- `home.0011_alter_homepage_body`
- `home.0012_alter_homepage_body`
- `website.0007_order_orderitem`
- `website.0008_order_payment_id`
- `website.0009_order_payment_idempotence_key`
- … (0010–0015 — см. `git log`)
- `website.0016_order_checkout_token` (2026-09-30)

**Важно для production-конфигурации (с 2026-09-30):**
- `ALLOWED_HOSTS` больше не `*`: meadowshore.ru, www.meadowshore.ru + дополнительные из `ALLOWED_HOSTS` в `.env`.
- Wagtail `Site` (Настройки → Сайты) должен иметь hostname `meadowshore.ru`, port 443. С `localhost` Wagtail строит внутренние запросы на недопустимый host — падают автосоздание редиректов при смене slug и превью страниц.
- Все slug страниц латинские (`LatinSlugMixin`); `latinize_slugs --apply` в `deploy.yml` идемпотентен.

Деплой описан в [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Стек

- **Django** 4.2 + **Wagtail** 5.2 (CMS для контентных страниц)
- `HomePage` — контент главной через Wagtail **StreamField** (блоки: hero, featured_products, about, observation, marquee, collections, features, а также ещё не размещённые на странице `fabric`, `usp_strip`, `philosophy`, `cta`)
- `website` — приложение каталога/корзины/заказов (`ProductPage`, `CatalogPage`, `Order`/`OrderItem`, избранное, checkout)
- `accounts` — регистрация/логин/личный кабинет
- Общий CSS — `static/css/style.css`, общий JS — `static/js/main.js`
- Переиспользуемые product-компоненты — `templates/includes/product_card.html`, `templates/includes/product_carousel.html` (используются каталогом, избранным, корзиной и главной; для главной — через `card_variant="homepage"`, не меняя дефолтную ветку)
- SQLite локально, PostgreSQL/файловая БД на проде (см. `meadowshore/settings/production.py`)
- Настройки разделены: `meadowshore/settings/{base,dev,production}.py`, конфиг через `python-decouple` (`.env`)

---

## Бренд

- Название: **Meadow Shore**
- Основной язык публичной коммуникации сайта — **русский**. Английские декоративные подписи (`SHOP`, `COLLECTION`, `FIELD NOTES`, `OBSERVATION` и т.п.) не используются — минимизировать англицизмы ради fashion-эстетики бренда.
- Первая коллекция называется **«Лесные жители»** — это единственное публичное имя. `Forest Dwellers` НЕ используется как публичное название (допустимо только как внутренний технический идентификатор, если где-то возникает).
- Сайт = интернет-магазин **и** визуальный архив бренда (система «Наблюдений» — короткие визуальные записи о животном/растении/месте).
- Полные правила бренда (характер, палитра, шрифты, что нельзя ломать) — в [site-redesign-progress.md](site-redesign-progress.md), разделы 3–5.

---

## Что выполнено на главной

### GLOBAL-01 — техническая база
- Адаптивная шапка: mobile/tablet до 1023px, desktop с 1024px (порог сдвинут с 768px, где раньше был баг с выездом иконок за viewport).
- Исправлено зависание мобильного meню (drawer) при ресайзе с mobile на desktop без перезагрузки.
- Hero CTA использует реальное Wagtail-поле `cta_url` (с fallback на `/catalog/`), а не жёстко зашитый якорь.

### HOME-01 — Hero
Editorial-Hero вместо e-commerce-версии. Утверждённые тексты (production-значения):

| Поле | Значение |
|---|---|
| eyebrow | `КОЛЛЕКЦИЯ 01 · ЛЕСНЫЕ ЖИТЕЛИ` |
| H1 | `Для нас лес — место, куда мы приходим. Для них — дом.` |
| subheadline | `Первая коллекция одежды Meadow Shore посвящена тем, кто остаётся в лесу после того, как мы уходим.` |
| CTA | `Смотреть коллекцию` → `/catalog/` |

### HOME-02 — подача товаров на главной («Первая коллекция»)
Редакционная подборка вместо стандартных e-commerce карточек.

| Поле | Значение |
|---|---|
| eyebrow | `ПЕРВАЯ КОЛЛЕКЦИЯ` |
| H2 | `Лесные жители` |
| CTA секции | `Смотреть всю коллекцию →` → `/catalog/` |

Карточки `card_variant="homepage"`: нет «Добавить в корзину», нет «Смотреть вещь», нет discount badge; кликабельны только фото и название; карточка заканчивается ценой. **Каталог (`/catalog/`) визуально не изменён** — используется тот же компонент с дефолтной веткой.

### HOME-03 — «О коллекции»
| Поле | Значение |
|---|---|
| tagline | `О КОЛЛЕКЦИИ` |
| H2 | `Лесные жители` |
| body | «Мы проходим по тропе и возвращаемся обратно. Птицы остаются на ветках. Белка продолжает движение между деревьями. Заяц исчезает в траве. Ёж выходит, когда становится тише.» / «"Лесные жители" — первая коллекция Meadow Shore о мире, который существует независимо от нашего присутствия. Каждый рисунок начинается с наблюдения за животным и его средой, а затем становится принтом или вышивкой на одежде.» / «Так часть места, в котором хочется остаться, можно унести с собой.» |

### HOME-04 — новый блок «Наблюдение» (`ObservationSectionBlock`)
Первый элемент фирменной системы «Наблюдений». Поля: `eyebrow`, `title`, `body`, `image`, опционально `caption`. CTA в Observation отсутствует принципиально.

| Поле | Значение |
|---|---|
| eyebrow | `НАБЛЮДЕНИЕ № 01` |
| title | `Певчая птица` |
| body | «Небольшую птицу среди ветвей можно не заметить сразу. Сначала взгляд цепляется за движение, затем за силуэт, и только потом — за цвет перьев среди хвои.» / «Так появилась одна из первых птиц Meadow Shore: не отдельный декоративный символ, а часть леса вокруг неё. В рисунке остаются ветви, хвоя, шишки и небольшие ягоды — среда важна не меньше самого животного.» |

Полная техническая история (архитектурные решения, находки, что нельзя ломать) — [site-redesign-progress.md](site-redesign-progress.md).

---

## Следующие задачи главной

- **HOME-05** — Материалы (блок на базе `FabricSectionBlock`)
- **HOME-06** — съёмка коллекции
- **HOME-07** — Архив природы
- **HOME-08** — О Meadow Shore
- **HOME-09** — письма Meadow Shore
- **HOME-10** — footer
- **HOME-11** — responsive/accessibility/performance/final QA

---

## ЮKassa — завершено и в production

Оплата картой через ЮKassa задеплоена в составе commit `47afaea` (2026-08-26) и подтверждена владельцем проекта как рабочая на production (реальная оплата на сайте проверена вручную, 2026-09-05).

Реализовано (см. `website/payments.py`, `website/models.py`, `website/views.py`, `website/urls.py`, `website/admin.py`, `website/notifications.py`, `website/stock.py`, миграции `0008_order_payment_id`, `0009_order_payment_idempotence_key`, тесты `website/tests/test_payments.py`):
- Создание платежа и редирект пользователя на оплату.
- Webhook/callback от ЮKassa, обновление статуса заказа.
- Idempotence key для защиты от повторной обработки.
- Уведомления о заказе (`website/notifications.py`).

Следующая приоритетная задача проекта — продолжение редизайна главной, **HOME-05** (см. раздел «Следующие задачи главной» выше).

---

## Source of truth

- **Текущее состояние проекта** — этот файл (`docs/PROJECT_STATE.md`)
- **Деплой** — [DEPLOYMENT.md](DEPLOYMENT.md)
- **История изменений** — [CHANGELOG.md](../CHANGELOG.md)
- **Инструкции для Claude Code** — [CLAUDE.md](../CLAUDE.md)
- **Исторические снапшоты** — `docs/handoffs/`
- **Детальный технический журнал редизайна главной** — [site-redesign-progress.md](site-redesign-progress.md) (рабочий журнал, дополняет, не дублирует этот файл)
