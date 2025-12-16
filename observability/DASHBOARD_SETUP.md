# Настройка дашборда Grafana "Microservices Overview"

## Описание дашборда

Дашборд содержит 3 панели:

1. **Request rate by service** - скорость запросов по каждому сервису
2. **Error rate (5xx) by service** - скорость ошибок 5xx по каждому сервису
3. **Request duration p95** - 95-й перцентиль длительности запросов

## Способ 1: Импорт готового дашборда (рекомендуется)

### Шаг 1: Откройте Grafana

1. Откройте браузер: http://localhost:3000
2. Войдите: `admin` / `admin`

### Шаг 2: Импортируйте дашборд

1. В левом меню нажмите на иконку **Dashboards** (четыре квадрата)
2. Нажмите **New** → **Import** (или кнопку **Import** в правом верхнем углу)
3. Нажмите **Upload JSON file**
4. Выберите файл: `observability/grafana-dashboard.json`
5. Нажмите **Load**
6. В поле **Prometheus** выберите **Prometheus** (data source должен быть уже настроен)
7. Нажмите **Import**

Готово! Дашборд создан и должен отображаться в списке дашбордов.

## Способ 2: Создание вручную

### Шаг 1: Создайте новый дашборд

1. В Grafana: **Dashboards** → **New Dashboard**
2. Нажмите **Add visualization**

### Шаг 2: Панель 1: Request rate by service

1. В выпадающем списке выберите **Prometheus**
2. В поле запроса введите:
   ```
   sum by (service) (rate(http_requests_total[5m]))
   ```
3. В настройках панели:
   - **Title**: `Request rate by service`
   - **Unit**: `reqps` (requests per second)
   - **Legend**: `{{service}}`
4. Нажмите **Apply**

### Шаг 3: Панель 2: Error rate (5xx) by service

1. Нажмите **Add panel** → **Add visualization**
2. В выпадающем списке выберите **Prometheus**
3. В поле запроса введите:
   ```
   sum by (service) (rate(http_requests_total{status_code=~"5.."}[5m]))
   ```
4. В настройках панели:
   - **Title**: `Error rate (5xx) by service`
   - **Unit**: `reqps`
   - **Legend**: `{{service}}`
5. Нажмите **Apply**

### Шаг 4: Панель 3: Request duration p95

1. Нажмите **Add panel** → **Add visualization**
2. В выпадающем списке выберите **Prometheus**
3. В поле запроса введите:
   ```
   histogram_quantile(0.95, sum by (le, service) (rate(http_request_duration_seconds_bucket[5m])))
   ```
4. В настройках панели:
   - **Title**: `Request duration p95`
   - **Unit**: `s` (seconds)
   - **Legend**: `{{service}}`
5. Нажмите **Apply**

### Шаг 5: Сохраните дашборд

1. Нажмите **Save dashboard** (иконка дискеты)
2. Введите название: **Microservices Overview**
3. Нажмите **Save**

## Настройка времени обновления

1. В правом верхнем углу дашборда нажмите на время (например, "Last 15 minutes")
2. Выберите **Last 15 minutes**
3. Нажмите на иконку обновления (кружок со стрелкой)
4. Выберите **10s** (обновление каждые 10 секунд)

## Объяснение запросов

### Request rate by service

```
sum by (service) (rate(http_requests_total[5m]))
```

- `http_requests_total` - общее количество HTTP запросов
- `rate(...[5m])` - скорость запросов за 5 минут
- `sum by (service)` - суммирование по сервисам

### Error rate (5xx) by service

```
sum by (service) (rate(http_requests_total{status_code=~"5.."}[5m]))
```

- `{status_code=~"5.."}` - фильтр только для статус кодов 5xx (500-599)
- Остальное аналогично первой панели

### Request duration p95

```
histogram_quantile(0.95, sum by (le, service) (rate(http_request_duration_seconds_bucket[5m])))
```

- `http_request_duration_seconds_bucket` - гистограмма длительности запросов
- `histogram_quantile(0.95, ...)` - вычисление 95-го перцентиля
- `sum by (le, service)` - суммирование по buckets (le) и сервисам

## Проверка работы

После создания дашборда:

1. Сделайте несколько запросов к микросервисам:

   ```powershell
   Invoke-WebRequest http://localhost:8001/health
   Invoke-WebRequest http://localhost:8002/health
   ```

2. Подождите 10-30 секунд

3. Обновите дашборд (F5 или кнопка обновления)

4. Вы должны увидеть данные на графиках

## Если панели показывают "No data"

1. Убедитесь, что Prometheus собирает метрики:

   - Откройте http://localhost:9090
   - Введите запрос: `http_requests_total`
   - Должны быть результаты

2. Убедитесь, что были сделаны запросы к микросервисам

3. Проверьте, что временной диапазон правильный (Last 15 minutes)

4. Убедитесь, что data source настроен правильно:
   - **Configuration** → **Data sources** → **Prometheus**
   - Должен быть статус "Health: Data source is working"
