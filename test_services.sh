#!/bin/bash

# Скрипт для проверки работоспособности всех сервисов

echo "Проверка работоспособности микросервисов..."
echo ""

services=(
    "http://localhost:8001/health"
    "http://localhost:8002/health"
    "http://localhost:8003/health"
    "http://localhost:8004/health"
    "http://localhost:8005/health"
    "http://localhost:8006/health"
    "http://localhost:8007/health"
    "http://localhost:8008/health"
)

service_names=(
    "Auth Service"
    "Profile Service"
    "Jobs Service"
    "Applications Service"
    "Reviews Service"
    "Mailing Service"
    "Verification Service"
    "Notifications Service"
)

for i in "${!services[@]}"; do
    echo -n "Проверка ${service_names[$i]}... "
    if curl -s -f "${services[$i]}" > /dev/null 2>&1; then
        echo "✓ OK"
    else
        echo "✗ FAILED"
    fi
done

echo ""
echo "Проверка завершена!"

