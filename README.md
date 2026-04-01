# upstream-viewer

Небольшой внутренний сервис для просмотра конфигурации **upstream** в Nginx: статическая страница в браузере показывает, какие `server_name` в каких файлах завязаны на какие `proxy_pass` и списки бэкендов. Данные собирает скрипт `update_upstreams.py`, обходя каталоги с конфигами (например `/etc/nginx/conf.d` и `/etc/nginx/sites-available`) и записывая снимок в `data/hosts.json`; фронтенд только читает этот JSON.

Продакшен-структура для Debian + Nginx с двумя отдельными версиями проекта:

- `python3/` — версия под Python 3
- `python2/` — версия под Python 2

Каждая папка содержит полноценный набор:

- `index.html`, `styles.css`, `script.js`
- `update_upstreams.py`
- `README.md` с установкой, примером nginx и cron (`*/10 * * * *`)

## Как использовать

- Debian + Python 3: см. `python3/README.md`
- Debian + Python 2: см. `python2/README.md`

Страница в проде отдаётся по префиксу `/upstream-viewer/` (см. пример `server` в README выбранной версии).
