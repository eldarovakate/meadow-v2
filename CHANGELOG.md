# Changelog

Формат: дата — заголовок релиза/этапа, затем Added/Changed/Production/Pending где уместно. Записи идут от новых к старым.

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
