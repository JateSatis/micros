# Пошаговая инструкция по настройке CI/CD

## Обзор

Настроены два CI/CD конвейера:

1. **auth-service** → DockerHub (непрерывная интеграция и доставка)
2. **profile-service** → Yandex Cloud (непрерывная интеграция и развертывание)

---

## Часть 1: Настройка auth-service для DockerHub

### Шаг 1: Создание аккаунта на DockerHub

1. Перейдите на https://hub.docker.com/
2. Зарегистрируйте аккаунт или войдите в существующий
3. Запомните ваш username

### Шаг 2: Настройка секретов в GitHub

1. Перейдите в ваш GitHub репозиторий
2. Откройте **Settings** → **Secrets and variables** → **Actions**
3. Нажмите **New repository secret**
4. Добавьте следующие секреты:

   **DOCKER_USERNAME**

   - Name: `DOCKER_USERNAME`
   - Value: ваш username на DockerHub (например: `myusername`)

   **DOCKER_PASSWORD**

   - Name: `DOCKER_PASSWORD`
   - Value: ваш пароль или Personal Access Token (рекомендуется)
   - Для создания токена: DockerHub → Account Settings → Security → New Access Token

### Шаг 3: Проверка работы

1. Сделайте commit и push изменений в папке `auth/` или в файл `.github/workflows/auth-dockerhub.yml`
2. Перейдите в **Actions** в вашем GitHub репозитории
3. Дождитесь завершения workflow
4. Проверьте на DockerHub: https://hub.docker.com/r/YOUR_USERNAME/auth-service

---

## Часть 2: Настройка profile-service для Yandex Cloud

### Шаг 1: Создание Container Registry в Yandex Cloud

1. Войдите в [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Выберите ваш каталог
3. Перейдите в **Container Registry** (или найдите через поиск)
4. Если реестра нет, нажмите **Создать реестр**
5. Назовите реестр по шаблону: `ikbo<номер_группы>` (например: `ikbo07`)
6. Запомните **ID реестра** (находится в информации о реестре)

### Шаг 2: Настройка сервисного аккаунта

1. В Yandex Cloud Console перейдите в **Сервисные аккаунты**
2. Найдите или создайте сервисный аккаунт `sa-cicd`
3. Убедитесь, что у аккаунта есть роли:
   - `container-registry.images.pusher` (для загрузки образов)
   - `serverless-containers.developer` (для развертывания контейнеров)
   - `iam.serviceAccounts.user` (для использования сервисного аккаунта)
4. Откройте сервисный аккаунт
5. Перейдите на вкладку **Авторизованные ключи**
6. Нажмите **Создать новый ключ** → **Создать авторизованный ключ**
7. В описании укажите: "CI/CD для profile-service"
8. Нажмите **Создать**
9. **ВАЖНО**: Скачайте JSON файл с ключами (он больше не будет показан!)

### Шаг 3: Создание Serverless Container

1. В Yandex Cloud Console перейдите в **Serverless Containers**
2. Нажмите **Создать контейнер**
3. Укажите название (должно начинаться с вашей фамилии, например: `ivanov-profile-service`)
4. Выберите сервисный аккаунт `sa-cicd`
5. Нажмите **Создать**
6. Запомните **ID контейнера** и **ID каталога** (folder-id)

### Шаг 4: Настройка публичного доступа

1. Откройте созданный контейнер
2. Перейдите в **Редактировать**
3. Включите **Публичный доступ**
4. Сохраните изменения

### Шаг 5: Настройка секретов в GitHub

1. В GitHub репозитории: **Settings** → **Secrets and variables** → **Actions**
2. Добавьте следующие секреты:

   **YC_REGISTRY_ID**

   - Name: `YC_REGISTRY_ID`
   - Value: ID вашего реестра (например: `crp1234567890abcdef`)

   **YC_KEYS**

   - Name: `YC_KEYS`
   - Value: содержимое JSON файла с ключами сервисного аккаунта (весь файл целиком)
   - Пример формата:
     ```json
     {
       "id": "...",
       "service_account_id": "...",
       "created_at": "...",
       "key_algorithm": "...",
       "public_key": "...",
       "private_key": "..."
     }
     ```

   **YC_CONTAINER_NAME**

   - Name: `YC_CONTAINER_NAME`
   - Value: имя вашего контейнера (например: `ivanov-profile-service`)

   **YC_FOLDER_ID**

   - Name: `YC_FOLDER_ID`
   - Value: ID каталога (folder-id) из Yandex Cloud

   **YC_SA_ID**

   - Name: `YC_SA_ID`
   - Value: ID сервисного аккаунта `sa-cicd`

   **ENV_DATABASE_URL**

   - Name: `ENV_DATABASE_URL`
   - Value: строка подключения к PostgreSQL
   - Пример: `postgresql://profile_user:profile_pass@51.250.26.59:5432/profile_db`
   - Или используйте вашу БД из docker-compose

   **ENV_JWT_SECRET**

   - Name: `ENV_JWT_SECRET`
   - Value: секретный ключ для JWT (например: `secret_key_for_jwt`)

   **ENV_AUTH_SERVICE_URL**

   - Name: `ENV_AUTH_SERVICE_URL`
   - Value: URL сервиса авторизации
   - Если auth-service тоже развернут в Yandex Cloud, укажите его URL
   - Или используйте публичный URL вашего auth-service

### Шаг 6: Проверка работы

1. Сделайте commit и push изменений в папке `profile/` или в файл `.github/workflows/profile-yandex.yml`
2. Перейдите в **Actions** в GitHub
3. Дождитесь завершения workflow (два job: build-and-push-to-yc и deploy)
4. Проверьте в Yandex Cloud:
   - Container Registry: должен появиться образ `profile-service`
   - Serverless Containers: должна появиться новая ревизия контейнера
5. Проверьте публичный URL контейнера (будет показан в консоли Yandex Cloud)

---

## Структура файлов

```
.github/
  workflows/
    auth-dockerhub.yml      # CI/CD для auth-service → DockerHub
    profile-yandex.yml      # CI/CD для profile-service → Yandex Cloud
```

## Триггеры запуска

Workflow запускаются автоматически при:

- Push в ветку `master` или `main`
- Создании Pull Request в `master` или `main`
- Изменениях в соответствующих папках (`auth/` или `profile/`)

## Отладка

### Проблемы с DockerHub

1. Проверьте правильность `DOCKER_USERNAME` и `DOCKER_PASSWORD`
2. Убедитесь, что используете Personal Access Token, а не пароль
3. Проверьте логи в GitHub Actions

### Проблемы с Yandex Cloud

1. Проверьте все секреты в GitHub
2. Убедитесь, что сервисный аккаунт имеет нужные роли
3. Проверьте, что реестр и контейнер созданы
4. Проверьте логи в GitHub Actions
5. Проверьте логи в Yandex Cloud Console → Serverless Containers → Логи

### Проблемы с развертыванием

1. Проверьте переменные окружения (особенно `DATABASE_URL`)
2. Убедитесь, что база данных доступна из интернета
3. Проверьте, что включен публичный доступ у контейнера
4. Проверьте health endpoint: `https://YOUR_CONTAINER_URL/health`

---

## Дополнительные настройки

### Изменение ресурсов контейнера

В файле `.github/workflows/profile-yandex.yml` можно изменить:

- `revision-cpu`: количество vCPU (по умолчанию: 1)
- `revision-memory`: объем памяти (по умолчанию: 512M)

### Добавление других переменных окружения

Добавьте их в секцию `revision-env` в workflow файле.

### Использование тегов версий

Образы помечаются тегами:

- `latest` - всегда последняя версия
- `${{ github.sha }}` - конкретный commit

Можно использовать теги версий, изменив workflow файлы.
