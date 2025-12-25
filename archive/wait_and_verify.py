#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для ожидания завершения парсинга и сравнения с реальными данными"""

import requests
import json
import time
import os
import sys

BASE_URL = "http://localhost:8000"
password = os.getenv("SITE_PASSWORD", "admin123")
task_id = "11b4b357-4ebc-42ec-89e8-3fc1f947fb89"  # Текущая задача

session = requests.Session()

print("Авторизация...")
session.get(f"{BASE_URL}/login")
resp = session.post(f"{BASE_URL}/login", data={"password": password}, allow_redirects=True)
if "login" not in resp.url.lower() or resp.url.endswith("/"):
    print("✓ Авторизация успешна")
else:
    print("✗ Ошибка авторизации")
    sys.exit(1)

print(f"\nОжидание завершения задачи {task_id}...")
print(f"URL: {BASE_URL}/tasks/{task_id}")
max_wait = 600
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
                print(f"\n✓ Завершено за {elapsed} сек")
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
    print(f"\n{card.get('source', 'unknown').upper()}: {card.get('card_url', 'N/A')}")
    print(f"  Проверьте:")
    print(f"    - Общее количество отзывов")
    print(f"    - Количество отзывов с ответами")
    print(f"    - Рейтинг карточки")
    print(f"    - Классификация по рейтингам (положительные/отрицательные/нейтральные)")

if issues:
    print(f"\n⚠️  Найдено проблем: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")
else:
    print(f"\n✓ Все данные соответствуют!")

