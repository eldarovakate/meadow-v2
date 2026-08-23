# Deployment

Как задеплоить `meadow-v2` на production (https://meadowshore.ru/).

> **Этот репозиторий публичный.** IP-адрес, пользователь и пути production-сервера здесь намеренно не дублируются — они уже присутствуют в `.github/workflows/deploy.yml` (доступном на GitHub), но повторно фиксировать инфраструктурные детали в отдельном документе для публичного репозитория — плохая практика. За точными значениями (хост, путь проекта, systemd unit) — к владельцу проекта или в сам workflow-файл; SSH-ключ хранится в GitHub Secrets, не в репозитории.

---

## Автоматический деплой (основной способ)

Каждый push в `main` triggers `.github/workflows/deploy.yml`:
1. GitHub Actions подключается к production-серверу по SSH (ключ — `secrets.SSH_PRIVATE_KEY`).
2. `git pull` в директории проекта на сервере.
3. `python manage.py migrate --noinput`
4. `python manage.py collectstatic --noinput`
5. `systemctl restart` сервиса приложения.

Это означает: **push в `main` = production deploy.** Не пушить в `main`, пока нет явного разрешения владельца проекта деплоить именно это изменение.

---

## Ручной деплой (если нужно вмешаться на сервере)

Общая последовательность (хост/путь — см. владельца проекта или workflow-файл):

```bash
cd <project-path>
source venv/bin/activate
```

Проверить состояние перед обновлением:

```bash
git status
git fetch origin
git pull --ff-only origin main
```

Если добавились миграции:

```bash
DJANGO_SETTINGS_MODULE=meadowshore.settings.production python manage.py migrate
```

Если менялись статические файлы:

```bash
DJANGO_SETTINGS_MODULE=meadowshore.settings.production python manage.py collectstatic --noinput
```

Перезапуск сервиса и проверка статуса:

```bash
systemctl restart <service-name>
systemctl is-active <service-name>
```

Проверка после деплоя:

```bash
DJANGO_SETTINGS_MODULE=meadowshore.settings.production python manage.py check
```

Логи сервиса:

```bash
journalctl -u <service-name> -n 50
```

---

## Важные оговорки

- **nginx** не перезапускать без изменения его конфигурации.
- **Wagtail dev-БД не переносится через Git** — контент production Wagtail независим от dev.
- **Production Wagtail content может потребовать ручного обновления** через admin-панель после деплоя кода (например, новые тексты StreamField-блоков, утверждённые в [PROJECT_STATE.md](PROJECT_STATE.md), нужно выставить руками — миграция меняет только структуру блоков, не контент).

---

## Rollback

Если после деплоя обнаружена регрессия:

1. Определить последний рабочий commit (см. [CHANGELOG.md](../CHANGELOG.md) или `git log`).
2. На сервере: `git checkout <last-good-sha>` (или `git revert` в `main` и обычный деплой — предпочтительнее, так как не уводит сервер в detached HEAD).
3. Если откат включает миграции, применённые после `<last-good-sha>` — **не применять `migrate` в обратную сторону вслепую**; сначала проверить, есть ли у отменяемых миграций безопасный `RunPython.reverse_code` или достаточно оставить схему как есть до следующего forward-fix.
4. `collectstatic --noinput`, затем restart сервиса.
5. Обновить [PROJECT_STATE.md](PROJECT_STATE.md) и [CHANGELOG.md](../CHANGELOG.md) с фактическим текущим production commit.

Не запускать `git reset --hard`/`clean -f` на production без явного разрешения владельца — там может быть незакоммиченная ручная правка (см. прецедент: `f05117b Track production LOGGING config (was applied manually on server, not committed)`).
