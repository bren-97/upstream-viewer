# upstream-viewer

Веб-страница со списком хостов (`server_name`) и их upstream из конфигов Nginx.

## Что учитывается

- Конфиги сайтов: `/etc/nginx/sites-available`
- Конфиги upstream: `/etc/nginx/conf.d`
- Парсер читает оба каталога и связывает `proxy_pass` с `upstream`, даже если они находятся в разных файлах.

По умолчанию используются оба пути через переменную `NGINX_CONFIG_DIRS`:

```bash
NGINX_CONFIG_DIRS="/etc/nginx/sites-available,/etc/nginx/conf.d"
```

## Установка и запуск

### 1) Локальный запуск

```bash
cd /opt/upstream-viewer
python3 server.py
```

Открыть: `http://127.0.0.1:8000`

### 2) Запуск как systemd-сервис (рекомендуется для production)

Пример unit-файла `/etc/systemd/system/upstream-viewer.service`:

```ini
[Unit]
Description=Upstream Viewer
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/upstream-viewer
Environment="HOST=127.0.0.1"
Environment="PORT=8000"
Environment="NGINX_CONFIG_DIRS=/etc/nginx/sites-available,/etc/nginx/conf.d"
ExecStart=/usr/bin/python3 /opt/upstream-viewer/server.py
Restart=always
RestartSec=3
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

Команды:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now upstream-viewer
sudo systemctl status upstream-viewer
```

## Варианты запуска сервиса

- Постоянный веб-сервис (`systemd`)  
  Самый простой и надежный вариант: страница всегда отдает актуальные данные по запросу.

- Через cron (периодический снимок, например раз в сутки)  
  Подходит, если не нужен онлайн-парсинг и хотите минимизировать runtime-процессы.

- Обновление по событию reload nginx  
  Можно запускать отдельный update-скрипт в `ExecReload` nginx unit или через inotify/systemd path units.

## Вариант с cron

Идея: хранить JSON-снимок и обновлять его по расписанию.

Пример cron:

```cron
0 3 * * * /usr/bin/python3 /opt/upstream-viewer/server.py --dump-json /var/lib/upstream-viewer/hosts.json
```

Для этого нужно добавить в `server.py` режим `--dump-json` (сейчас не реализован).

## Вариант обновления при reload nginx

Если у вас `nginx.service` управляется systemd, можно добавить post-reload hook, который запускает скрипт обновления данных.  
Это дает почти мгновенную синхронизацию после `nginx -s reload` или `systemctl reload nginx`.
