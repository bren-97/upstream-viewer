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

Файл: `/etc/nginx/conf.d/upstream-viewer.example.com.conf`

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
