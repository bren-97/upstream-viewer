# upstream-viewer

Продакшен-структура для Debian + Nginx с двумя отдельными версиями проекта:

- `python3/` - версия под Python 3
- `python2/` - версия под Python 2

Каждая папка содержит полноценный набор:
- `index.html`, `styles.css`, `script.js`
- `update_upstreams.py`
- `README.md` с установкой, nginx-конфигом и cron (`*/10 * * * *`)

## Как использовать

- Для Debian с Python 3: `python3/README.md`
- Для Debian с Python 2: `python2/README.md`
# upstream-viewer

Продакшен-структура для Debian + Nginx с двумя отдельными версиями проекта:

- `python3/` - версия под Python 3
- `python2/` - версия под Python 2

Каждая папка содержит полноценный набор:
- `index.html`, `styles.css`, `script.js`
- `update_upstreams.py`
- свой `README.md` с установкой, nginx-конфигом и cron (`*/10 * * * *`)

## Как использовать

- Для Debian с Python 3: `python3/README.md`
- Для Debian с Python 2: `python2/README.md`
# upstream-viewer

Репозиторий разделен на два самостоятельных варианта проекта:

- `python3/` - полная версия под Python 3
- `python2/` - полная версия под Python 2

В каждой папке лежат:
- `index.html`, `styles.css`, `script.js` (веб-страница)
- `update_upstreams.py` (генерация `/var/www/upstream-viewer/data/hosts.json`)
- `README.md` с установкой, nginx-конфигом и cron (раз в 10 минут)

## Быстрый старт

- Если на хосте есть Python 3: используйте `python3/README.md`
- Если нужен legacy Python 2: используйте `python2/README.md`
# upstream-viewer

Статическая веб-страница со списком `server_name` и их upstream из конфигов Nginx.

Проект адаптирован под схему:
- контент страницы в `/var/www/upstream-viewer`
- nginx-конфиг страницы в `/etc/nginx/conf.d`
- скрипт обновления данных в `/opt/upstream-viewer`
- обновление данных через `cron` каждые 10 минут

## Версии скрипта

- `update_upstreams_py3.py` - версия для Python 3
- `update_upstreams_py2.py` - версия для Python 2
- `server.py` - текущая копия версии Python 3 (для обратной совместимости в репозитории)

## Структура проекта

- `index.html` - страница
- `styles.css` - стили
- `script.js` - загрузка и отображение данных из JSON (`/data/hosts.json`)

## Установка

### 1) Разложить файлы

```bash
sudo mkdir -p /var/www/upstream-viewer/data
sudo mkdir -p /opt/upstream-viewer

sudo cp index.html styles.css script.js /var/www/upstream-viewer/
```

### 2) Выбрать версию скрипта

#### Вариант A: Python 3

```bash
sudo cp update_upstreams_py3.py /opt/upstream-viewer/update_upstreams.py
sudo chmod +x /opt/upstream-viewer/update_upstreams.py
```

#### Вариант B: Python 2

```bash
sudo cp update_upstreams_py2.py /opt/upstream-viewer/update_upstreams.py
sudo chmod +x /opt/upstream-viewer/update_upstreams.py
```

### 3) Настроить Nginx в `/etc/nginx/conf.d`

Пример: `/etc/nginx/conf.d/upstream-viewer.example.com.conf`

```nginx
server {
    listen 80;
    server_name upstream-viewer.example.com;

    root /var/www/upstream-viewer;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /data/ {
        add_header Cache-Control "no-store";
    }
}
```

`server_name` должен совпадать с хостнеймом, по которому открывается страница.

Проверка и применение:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 4) Первый запуск генерации JSON

#### Python 3

```bash
sudo /usr/bin/python3 /opt/upstream-viewer/update_upstreams.py \
  --config-dirs /etc/nginx/conf.d,/etc/nginx/sites-available \
  --output /var/www/upstream-viewer/data/hosts.json
```

#### Python 2

```bash
sudo /usr/bin/python2 /opt/upstream-viewer/update_upstreams.py \
  --config-dirs /etc/nginx/conf.d,/etc/nginx/sites-available \
  --output /var/www/upstream-viewer/data/hosts.json
```

## Cron: запуск каждые 10 минут

Выберите строку под вашу версию Python.

#### Python 3

```cron
*/10 * * * * /usr/bin/python3 /opt/upstream-viewer/update_upstreams.py --config-dirs /etc/nginx/conf.d,/etc/nginx/sites-available --output /var/www/upstream-viewer/data/hosts.json >/var/log/upstream-viewer-cron.log 2>&1
```

#### Python 2

```cron
*/10 * * * * /usr/bin/python2 /opt/upstream-viewer/update_upstreams.py --config-dirs /etc/nginx/conf.d,/etc/nginx/sites-available --output /var/www/upstream-viewer/data/hosts.json >/var/log/upstream-viewer-cron.log 2>&1
```

Проверить:

```bash
sudo crontab -l
```

## Что читает скрипт

- По умолчанию читает файлы из:
  - `/etc/nginx/conf.d`
  - `/etc/nginx/sites-available`
- Игнорирует типичные временные/backup-файлы (`.*`, `*~`, `*.bak`, `*.swp`, `*.tmp`, `*.dpkg-old`, `*.dpkg-dist`, `*.disabled`)
- Ищет:
  - блоки `server { ... }` и `server_name`
  - `proxy_pass ...`
  - блоки `upstream NAME { ... }` и backend `server ...`

Если upstream и server-блоки лежат в разных файлах внутри этих каталогов, они корректно связываются.
# upstream-viewer

Статическая веб-страница со списком `server_name` и их upstream из конфигов Nginx.

Проект адаптирован под схему:
- контент страницы в `/var/www/upstream-viewer`
- nginx-конфиг страницы в `/etc/nginx/conf.d`
- Python3-скрипт обновления данных в `/opt/upstream-viewer`
- обновление данных через `cron` каждые 10 минут

## Структура проекта

- `index.html` - страница
- `styles.css` - стили
- `script.js` - загрузка и отображение данных из JSON
- `server.py` - Python3-скрипт генерации `/var/www/upstream-viewer/data/hosts.json`

## Установка

### 1) Разложить файлы

```bash
sudo mkdir -p /var/www/upstream-viewer/data
sudo mkdir -p /opt/upstream-viewer

sudo cp index.html styles.css script.js /var/www/upstream-viewer/
sudo cp server.py /opt/upstream-viewer/update_upstreams.py
sudo chmod +x /opt/upstream-viewer/update_upstreams.py
```

### 2) Настроить Nginx в `/etc/nginx/conf.d`

Пример: `/etc/nginx/conf.d/upstream-viewer.example.com.conf`

```nginx
server {
    listen 80;
    server_name upstream-viewer.example.com;

    root /var/www/upstream-viewer;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /data/ {
        add_header Cache-Control "no-store";
    }
}
```

`server_name` должен совпадать с хостнеймом, по которому открывается страница.

Проверка и применение:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 3) Первый запуск генерации JSON

```bash
sudo /usr/bin/python3 /opt/upstream-viewer/update_upstreams.py \
  --config-dirs /etc/nginx/conf.d,/etc/nginx/sites-available \
  --output /var/www/upstream-viewer/data/hosts.json
```

После этого откройте ваш хостнейм в браузере.

## Cron: запуск каждые 10 минут

Добавьте в `crontab` (например, root):

```cron
*/10 * * * * /usr/bin/python3 /opt/upstream-viewer/update_upstreams.py --config-dirs /etc/nginx/conf.d,/etc/nginx/sites-available --output /var/www/upstream-viewer/data/hosts.json >/var/log/upstream-viewer-cron.log 2>&1
```

Проверить:

```bash
sudo crontab -l
```

## Что читает скрипт

- По умолчанию читает файлы из:
  - `/etc/nginx/conf.d`
  - `/etc/nginx/sites-available`
- Игнорирует типичные временные/backup-файлы (`.*`, `*~`, `*.bak`, `*.swp`, `*.tmp`, `*.dpkg-old`, `*.dpkg-dist`, `*.disabled`)
- Ищет:
  - блоки `server { ... }` и `server_name`
  - `proxy_pass ...`
  - блоки `upstream NAME { ... }` и backend `server ...`

Если upstream и server-блоки лежат в разных файлах внутри этих каталогов, они корректно связываются.
