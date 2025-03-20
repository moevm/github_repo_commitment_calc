# Инструкция по разворачиванию Forgejo с использованием Docker
# чтобы запустить в Docker контейнере Forgejo необходимо выполнить команду:
docker-compose up -d

# На localhost:3000 открывается Forgejo, необходимо пройти регистрацию создать репозиторий

# Для подключения простейшего клиента к данному localhost необходимо передать ему ссылку на репозиторий и API токен
# Получение API токена для подключения клиента:

curl -H "Content-Type: application/json" -d '{"name":"test"}' -u username:password http://forgejo.your.host/api/v1/users/<username>/tokens