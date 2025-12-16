# Быстрое создание дашборда "Microservices Overview"

## Самый простой способ (импорт готового)

1. Откройте Grafana: http://localhost:3000
2. Войдите: `admin` / `admin`
3. **Dashboards** → **New** → **Import**
4. Нажмите **Upload JSON file**
5. Выберите файл: `observability/grafana-dashboard.json`
6. Нажмите **Load** → **Import**

Готово! Дашборд создан.

## Настройка времени обновления

После импорта:

1. В правом верхнем углу нажмите на время (например, "Last 15 minutes")
2. Выберите **Last 15 minutes**
3. Нажмите на иконку обновления (↻)
4. Выберите **10s**

## Проверка работы

1. Сделайте несколько запросов к микросервисам:

   ```powershell
   Invoke-WebRequest http://localhost:8001/health
   Invoke-WebRequest http://localhost:8002/health
   Invoke-WebRequest http://localhost:8003/health
   ```

2. Подождите 10-30 секунд

3. Обновите дашборд (F5)

4. Вы должны увидеть данные на графиках

## Что показывают панели

- **Request rate by service**: Сколько запросов в секунду получает каждый сервис
- **Error rate (5xx) by service**: Сколько ошибок 5xx в секунду (если есть)
- **Request duration p95**: 95% запросов выполняются быстрее этого времени

## Если панели показывают "No data"

1. Убедитесь, что Prometheus собирает метрики:

   - http://localhost:9090 → введите `http_requests_total`
   - Должны быть результаты

2. Убедитесь, что были сделаны запросы к микросервисам

3. Проверьте временной диапазон (Last 15 minutes)
