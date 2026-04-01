# upstream-viewer (Python 3)

Статическая страница в `/var/www/upstream-viewer` + генерация `hosts.json` скриптом на Python 3.

## Файлы

- `index.html`, `styles.css`, `script.js` - фронтенд
- `update_upstreams.py` - генератор `/var/www/upstream-viewer/data/hosts.json`

## Установка

```bash
cd python3
sudo mkdir -p /var/www/upstream-viewer/data
sudo mkdir -p /opt/upstream-viewer

sudo cp index.html styles.css script.js /var/www/upstream-viewer/
sudo cp update_upstreams.py /opt/upstream-viewer/update_upstreams.py
sudo chmod +x /opt/upstream-viewer/update_upstreams.py
```

## Nginx конфиг

Файл, например: `/etc/nginx/conf.d/upstream-viewer.conf`

```nginx
server {
    listen 127.0.0.1:80;
    server_name localhost;

    access_log /var/log/nginx/upstream-viewer.access.log;
    error_log  /var/log/nginx/upstream-viewer.error.log;

    location = /upstream-viewer {
        return 301 /upstream-viewer/;
    }

    location /upstream-viewer/ {
        alias /var/www/upstream-viewer/;
        index index.html;

        allow 127.0.0.1;
        allow 172.27.0.0/16;
        deny all;
    }

    location / {
        return 404;
    }
}
```

После деплоя страница доступна по адресу `http://127.0.0.1/upstream-viewer/` (JSON: `/upstream-viewer/data/hosts.json`).

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Первый запуск

```bash
sudo /usr/bin/python3 /opt/upstream-viewer/update_upstreams.py \
  --config-dirs /etc/nginx/conf.d,/etc/nginx/sites-available \
  --output /var/www/upstream-viewer/data/hosts.json
```

## Cron (каждые 10 минут)

```cron
*/10 * * * * /usr/bin/python3 /opt/upstream-viewer/update_upstreams.py --config-dirs /etc/nginx/conf.d,/etc/nginx/sites-available --output /var/www/upstream-viewer/data/hosts.json >/var/log/upstream-viewer-cron.log 2>&1
```
