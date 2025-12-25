#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Запуск парсинга для Победа digital и сравнение результатов"""

import requests
import json
import time
import os
import sys

BASE_URL = "http://localhost:8000"
password = os.getenv("SITE_PASSWORD", "admin123")

session = requests.Session()

print("="*80)
print("ЗАПУСК ПАРСИНГА ДЛЯ ПОБЕДА DIGITAL")
print("="*80)
print("Компания: Победа digital")
print("Сайт: http://pbd.space")
print("Источник: BOTH")
print("Область поиска: Страна / общий поиск — города: Санкт-Петербург, Москва")
print("="*80)

print("\nАвторизация...")
session.get(f"{BASE_URL}/login")
resp = session.post(f"{BASE_URL}/login", data={"password": password}, allow_redirects=True)
if "login" not in resp.url.lower() or resp.url.endswith("/"):
    print("✓ Авторизация успешна")
else:
    print("✗ Ошибка авторизации")
    sys.exit(1)

print("\nЗапуск парсинга...")
data = {
    "company_name": "Победа digital",
    "company_site": "http://pbd.space",
    "source": "both",
    "email": "test@example.com",
    "search_scope": "country",  # Страна / общий поиск
    "cities": "Санкт-Петербург, Москва"  # Города для поиска
}

resp = session.post(f"{BASE_URL}/start_parsing", data=data, allow_redirects=True)

if resp.status_code in [200, 302]:
    if "/tasks/" in resp.url:
        task_id = resp.url.split("/tasks/")[-1].split("?")[0].split("#")[0].split("&")[0]
        print(f"✓ Парсинг запущен!")
        print(f"Task ID: {task_id}")
        print(f"URL: {BASE_URL}/tasks/{task_id}")
    elif "active_task_id=" in resp.url:
        import urllib.parse
        parsed = urllib.parse.urlparse(resp.url)
        params = urllib.parse.parse_qs(parsed.query)
        if "active_task_id" in params:
            task_id = params["active_task_id"][0]
            print(f"✓ Используется активная задача: {task_id}")
        else:
            print("✗ Не удалось получить task_id")
            sys.exit(1)
    else:
        print("✗ Не удалось получить task_id из ответа")
        print(f"URL: {resp.url}")
        sys.exit(1)
else:
    print(f"✗ Ошибка запуска парсинга: {resp.status_code}")
    sys.exit(1)

print(f"\nОжидание завершения парсинга...")
max_wait = 900  # 15 минут
start = time.time()
status = None

while time.time() - start < max_wait:
    try:
        resp = session.get(f"{BASE_URL}/tasks/{task_id}/status", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            elapsed = int(time.time() - start)
            progress = data.get("progress", "")
            print(f"Статус: {status} | Прогресс: {progress} | Время: {elapsed} сек", end="\r")
            
            if status == "COMPLETED":
                print(f"\n✓ Парсинг завершен за {elapsed} сек")
                break
            elif status == "FAILED":
                print(f"\n✗ Ошибка: {data.get('error', 'Unknown error')}")
                sys.exit(1)
        else:
            print(f"\n⚠️  HTTP {resp.status_code}, повтор через 5 сек...")
    except Exception as e:
        print(f"\n⚠️  Ошибка соединения: {e}, повтор через 5 сек...")
    
    time.sleep(5)

if status != "COMPLETED":
    print(f"\n⚠️  Парсинг не завершен (статус: {status})")
    print(f"Проверьте статус вручную: {BASE_URL}/tasks/{task_id}")
    sys.exit(1)

print("\nСкачивание отчета...")
resp = session.get(f"{BASE_URL}/tasks/{task_id}/download-json")
if resp.status_code != 200:
    print(f"✗ Ошибка получения отчета: {resp.status_code}")
    sys.exit(1)

report_data = resp.json()
output_file = f"output/verification_report_{task_id}.json"
os.makedirs("output", exist_ok=True)
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(report_data, f, ensure_ascii=False, indent=2)
print(f"✓ Отчет сохранен: {output_file}")

print("\n" + "="*80)
print("ПРОВЕРКА РЕЗУЛЬТАТОВ")
print("="*80)

cards = report_data.get("cards", [])
statistics = report_data.get("statistics", {})

issues = []
all_ok = True

for card in cards:
    source = card.get("source", "unknown")
    card_name = card.get("card_name", "N/A")
    card_url = card.get("card_url", "N/A")
    
    print(f"\n{source.upper()}: {card_name}")
    print(f"URL: {card_url}")
    
    card_reviews = card.get("card_reviews_count", 0)
    stat_reviews = statistics.get(source, {}).get("aggregated_reviews_count", 0)
    detailed_count = len(card.get("detailed_reviews", []))
    
    print(f"  Отзывов в карточке: {card_reviews}")
    print(f"  Отзывов в статистике: {stat_reviews}")
    print(f"  Детальных отзывов: {detailed_count}")
    
    if card_reviews == stat_reviews and detailed_count == stat_reviews:
        print(f"  ✓ ВСЕ СООТВЕТСТВУЕТ!")
    else:
        all_ok = False
        print(f"  ⚠️  НЕСООТВЕТСТВИЯ:")
        if card_reviews != stat_reviews:
            issue = f"{source}: card_reviews_count ({card_reviews}) != aggregated_reviews_count ({stat_reviews})"
            print(f"    - {issue}")
            issues.append(issue)
        if detailed_count != stat_reviews:
            issue = f"{source}: детальных отзывов ({detailed_count}) != aggregated_reviews_count ({stat_reviews})"
            print(f"    - {issue}")
            issues.append(issue)

print("\n" + "="*80)
print("ОТКРОЙТЕ URL В БРАУЗЕРЕ И СРАВНИТЕ ДАННЫЕ")
print("="*80)
for card in cards:
    source = card.get("source", "unknown").upper()
    card_url = card.get("card_url", "N/A")
    card_name = card.get("card_name", "N/A")
    
    print(f"\n{source}: {card_name}")
    print(f"URL: {card_url}")
    print(f"  Проверьте на реальной странице:")
    print(f"    - Общее количество отзывов (ожидается: {card.get('card_reviews_count', 0)})")
    print(f"    - Рейтинг карточки (ожидается: {card.get('card_rating', 'N/A')})")
    print(f"    - Количество отзывов с ответами (ожидается: {card.get('card_answered_reviews_count', 0)})")
    print(f"    - Классификация по рейтингам:")
    print(f"      - Положительных: {card.get('card_reviews_positive', 0)}")
    print(f"      - Отрицательных: {card.get('card_reviews_negative', 0)}")
    print(f"      - Нейтральных: {card.get('card_reviews_neutral', 0)}")
    print(f"    - Детальные данные отзывов (при раскрытии карточки)")

if issues:
    print(f"\n⚠️  Найдено проблем: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
    print(f"\nРекомендуется проверить данные на реальных страницах по URL выше")
else:
    print(f"\n✓ Все данные в отчете соответствуют друг другу!")
    print(f"Рекомендуется также проверить данные на реальных страницах по URL выше")

print(f"\nОтчет сохранен: {output_file}")

