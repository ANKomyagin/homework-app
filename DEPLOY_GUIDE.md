# 🏗️ Инфраструктура и Деплой (EngTask + MaxMath)

Этот документ описывает, как два независимых проекта (`engtask.ru` и `maxmath.ru`) уживаются на одном VPS сервере, не мешая друг другу.

---

## 🌍 1. Главный Nginx (Шлюз)
На любом сервере порты **80 (HTTP)** и **443 (HTTPS)** могут быть заняты только одной программой. На нашем сервере эти порты захватил контейнер `maxmath_prod_nginx`.

Поэтому `engtask` **не пытается** привязаться к портам 80 или 443 (иначе докер выдаст ошибку `address already in use`).
Вместо этого `engtask` публикует свой собственный, внутренний Nginx на порту **8080** (смотри `docker-compose.yml`: `8080:80`).

### Как запросы доходят до EngTask?
Контейнер `maxmath_prod_nginx` выступает в роли "швейцара" (Reverse Proxy). Он смотрит на заголовок `Host` в запросе пользователя:
1. Если кто-то запрашивает `maxmath.ru` ➔ запрос идёт в контейнеры математики.
2. Если кто-то запрашивает `engtask.ru` ➔ срабатывает наш конфиг `engtask_proxy.conf`, и швейцар перебрасывает запрос по адресу `http://172.17.0.1:8080`.
*(Примечание: `172.17.0.1` — это стандартный IP-адрес самого сервера-хоста в подсети Docker).*

---

## ⚙️ 2. Как мы "подсунули" конфиг главному Nginx
Внутри `maxmath_prod_nginx` работает стандартный Nginx, который автоматически читает все `.conf` файлы из папки `/etc/nginx/conf.d/`.

Чтобы не портить git-историю проекта MaxMath, мы использовали файл **`docker-compose.override.yml`** (он лежит в `~/MaxMath/deploy/prod/`).
Этот файл автоматически подхватывается Докером и говорит ему: 
> *"Когда будешь запускать контейнер `nginx`, примонтируй файл `/root/engtask/engtask_proxy.conf` внутрь контейнера по пути `/etc/nginx/conf.d/engtask.conf`"*.

Таким образом, при любом обновлении MaxMath, настройки EngTask загружаются автоматически.

---

## 🔒 3. Как работают SSL-сертификаты (HTTPS)
Для выпуска бесплатных сертификатов используется **Certbot**. 
Чтобы Certbot убедился, что домен принадлежит нам, он создаёт временный проверочный файл, который должен быть доступен по адресу `http://engtask.ru/.well-known/acme-challenge/...`.

**Где лежат сертификаты?**
Проект MaxMath уже настроил удобные папки для Certbot:
- `~/MaxMath/deploy/prod/certbot/conf/` ➔ здесь лежат сами сертификаты.
- `~/MaxMath/deploy/prod/certbot/www/` ➔ здесь Certbot создаёт проверочные файлы.

Мы выпустили сертификат для `engtask.ru`, запустив временный контейнер `certbot`, который положил файлы в эти же самые папки. Наш `engtask_proxy.conf` просто читает их оттуда:
```nginx
ssl_certificate /etc/letsencrypt/live/engtask.ru/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/engtask.ru/privkey.pem;
```

---

## 🛠️ Шпаргалка по частым операциям

### 🔄 Как обновить EngTask (выкатить новый код)
Если ты внёс изменения в код на своём компьютере и запушил их на GitHub:
1. Зайди на сервер: `ssh root@45.151.101.176`
2. Перейди в папку: `cd ~/engtask`
3. Скачай обновления: `git pull`
4. Пересобери и перезапусти: `docker compose up -d --build`

### 📝 Если нужно изменить настройки домена (engtask_proxy.conf)
Если ты решишь поменять домен, добавить поддомен или изменить редиректы:
1. Отредактируй конфиг: `nano ~/engtask/engtask_proxy.conf`
2. Перезагрузи главный Nginx (чтобы он перечитал файл):
   `docker exec maxmath_prod_nginx nginx -s reload`

### ♻️ Продление SSL сертификатов
Let's Encrypt выдаёт сертификаты на 90 дней. Для продления всех сертификатов (и maxmath, и engtask) достаточно выполнить:
```bash
docker run -it --rm --name certbot \
  -v "/root/MaxMath/deploy/prod/certbot/conf:/etc/letsencrypt" \
  -v "/root/MaxMath/deploy/prod/certbot/www:/var/www/certbot" \
  certbot/certbot renew
```
И после этого сказать главному Nginx применить новые сертификаты:
```bash
docker exec maxmath_prod_nginx nginx -s reload
```
