# Changelog

Формат: дата — заголовок релиза/этапа, затем Added/Changed/Production/Pending где уместно. Записи идут от новых к старым.

---

## 2026-09-30 — Pre-launch hardening, латинские адреса, галерея

### Added
- Латинские адреса страниц: `website/slugs.py` (`LatinSlugMixin` на всех страницах `website`), команда `latinize_slugs` (переименовывает кириллические slug, Wagtail создаёт 301 со старых адресов); запускается в `deploy.yml` после `migrate`
- Защита от двойного POST checkout: `Order.checkout_token` (unique, миграция `website.0016_order_checkout_token`)
- Тесты `website/tests/test_launch_hardening.py` (29 шт.)

### Changed
- Галерея товара: стрелки поверх главного фото, появляются при наведении (на тач-устройствах видны всегда), свайп
- B3: первое уведомление — «Заказ №N создан, ожидает оплаты»; после оплаты — «Оплата подтверждена: заказ №N»
- O1: серверная проверка размера/количества/остатка в `reserve_stock_for_lines`; `/cart/update/` больше не создаёт новые строки
- O2: pending после возврата из ЮKassa — «Заказ ожидает оплаты» + «Перейти к оплате» на `confirmation_url` того же платежа
- O3: timeout запросов к ЮKassa (5 с connect / 15 с read — SDK сам timeout не ставит), `EMAIL_TIMEOUT = 10`, root-логгер WARNING в консоль на production
- A10: `ALLOWED_HOSTS` = meadowshore.ru, www + `.env` (без `*`), `SESSION/CSRF_COOKIE_SECURE = True`, CSRF origins только https, ссылка сброса пароля из `SITE_URL`
- A8: валидация и нормализация телефона (`+7XXXXXXXXXX`)
- A11: в корзину — только опубликованный товар со статусом «В наличии» и ценой

### Production
- Commits `3436cb5`, `1213221`, `60b21de` (production = `60b21de`)
- Migration `website.0016_order_checkout_token` — применена (проверено `showmigrations` на сервере)
- Django check passed, 59 тестов OK
- Ручные шаги на сервере 2026-09-30: в Wagtail `Site` hostname `localhost` → `meadowshore.ru`, port 443 (иначе при строгом `ALLOWED_HOSTS` падает автосоздание редиректов и превью Wagtail); `latinize_slugs --apply` выполнен вручную (6 страниц), редирект для первой страницы создан вручную; сервис перезапущен
- Проверено на проде: 7 латинских адресов → 200, 6 старых кириллических → 301, запрос с чужим Host → 400

### Pending
- Wagtail content: размеры и остатки «Ёж и яблоки», тексты доставки, убрать «[заполнить]» из юридических документов
- HSTS сознательно не включён

---

## 2026-08-26 — YooKassa payment flow

### Added
- Полноценная оплата картой через ЮKassa: создание платежа, редирект на оплату, webhook/callback, обновление статуса заказа
- Idempotence key для заказа (`website.0009_order_payment_idempotence_key`), защита от повторной обработки платежа
- Уведомления о заказе (`website/notifications.py`)
- Тесты платёжного флоу (`website/tests/test_payments.py`)

### Production
- Commit `47afaea`
- Migrations `website.0008_order_payment_id`, `website.0009_order_payment_idempotence_key`
- Django check passed
- Оплата на сайте проверена владельцем проекта вручную на production (2026-09-05) — работает

### Pending
- HOME-05 и следующие блоки главной (см. [PROJECT_STATE.md](docs/PROJECT_STATE.md))

---

## 2026-08-23 — Homepage redesign, phase 1

### Added
- Новый Hero коллекции «Лесные жители»
- Новый Wagtail block «Наблюдение» (`ObservationSectionBlock`)

### Changed
- Homepage product presentation (карточки главной отделены от каталога через `card_variant="homepage"`)
- История первой коллекции (блок «О коллекции»)
- Tablet/desktop header (порог адаптива сдвинут на 1024px)
- Mobile drawer behavior (исправлено зависание при ресайзе)

### Production
- Commit `0465819`
- Migrations `home.0010`–`home.0012`
- Django check passed

### Pending
- ЮKassa integration (не входит в этот release — см. [PROJECT_STATE.md](docs/PROJECT_STATE.md))
- HOME-05 и следующие блоки главной
