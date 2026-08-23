# CLAUDE.md

Инструкции для Claude Code при работе с репозиторием `meadow-v2` (Meadow Shore — Django 4.2 + Wagtail 5.2).

## Перед работой

Перед существенной задачей сначала читать:
1. Этот файл (`CLAUDE.md`)
2. [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) — актуальное состояние проекта
3. Релевантные документы из `docs/` (`DEPLOYMENT.md`, `site-redesign-progress.md`, `handoffs/`)
4. Раздел «Бренд» в `docs/PROJECT_STATE.md`, если задача касается UI/content/brand

Не проводить новый аудит проекта с нуля, если актуальное состояние уже описано в `docs/PROJECT_STATE.md`.

---

## Release & Deployment Protocol

### Commits
- Одна независимая задача = отдельный commit.
- Не смешивать дизайн, платежи, инфраструктуру и другие независимые задачи в одном commit.
- Перед staging обязательно проверять `git status`.
- Stage только файлы текущей задачи — не `git add .`/`git add -A`, если working tree содержит чужие незавершённые изменения.

### Запрещено коммитить
- secrets, `.env`, API keys, SSH keys
- DB dumps (`*dump*.json`), local backups (`*_local_backup_*`), production media backups

### Push
Не делать production push/deploy только потому, что задача завершена. Push в `main` = production deploy (см. `docs/DEPLOYMENT.md`) — выполнять только после явного разрешения владельца проекта, если он явно не попросил в текущей задаче выполнить push/release.

### Перед release
Обязательно:
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
git status
```
Запускать релевантные тесты, если они есть для затронутой области.

### После production release
Claude обязан:
1. Обновить `docs/PROJECT_STATE.md`.
2. Обновить `CHANGELOG.md`.
3. Зафиксировать: дату, commit SHA, миграции, результат Django check, выполненные задачи, pending work.
4. Явно разделить изменения кода и изменения Wagtail content (контент часто требует отдельного ручного шага в production admin).

### GitHub Release
После успешного production deployment: если GitHub CLI `gh` доступен, авторизован, и владелец разрешил release automation — создавать production GitHub Release.

Формат тега: `prod-YYYY-MM-DD-short-name`.

Release notes должны содержать: что изменилось (пользовательские и технические изменения), миграции, production SHA, результат validation/checks, что сознательно не вошло, следующие задачи.

Если `gh` недоступен — не устанавливать дополнительные инструменты без необходимости; подготовить готовые markdown release notes и дать владельцу одну конкретную инструкцию для оставшегося шага (создать tag/release вручную).

### Deployment
Не проводить повторный поиск инфраструктурных деталей (хост, project path, venv, systemd service), если они уже определены в `docs/DEPLOYMENT.md` и инфраструктура не менялась. Репозиторий публичный — не добавлять новые IP/root/инфраструктурные детали в tracked-документы без необходимости.
