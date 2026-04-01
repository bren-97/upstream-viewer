# upstream-viewer

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
