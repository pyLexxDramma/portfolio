#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Мониторинг текущего парсинга и запуск нового с правильными настройками"""

import requests
import time
import os
import sys

BASE_URL = "http://localhost:8000"
password = os.getenv("SITE_PASSWORD", "admin123")
current_task_id = "11b4b357-4ebc-42ec-89e8-3fc1f947fb89"

session = requests.Session()

print("Авторизация...")
session.get(f"{BASE_URL}/login")
resp = session.post(f"{BASE_URL}/login", data={"password": password}, allow_redirects=True)
if "login" not in resp.url.lower() or resp.url.endswith("/"):
    print("✓ Авторизация успешна")
else:
    print("✗ Ошибка авторизации")
    sys.exit(1)

print(f"\nПроверка статуса текущей задачи {current_task_id}...")
max_wait = 300  # Ждем максимум 5 минут
start = time.time()

while time.time() - start < max_wait:
    try:
        resp = session.get(f"{BASE_URL}/tasks/{current_task_id}/status", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            elapsed = int(time.time() - start)
            progress = data.get("progress", "")
            print(f"Статус: {status} | Прогресс: {progress} | Время: {elapsed} сек", end="\r")
            
            if status == "COMPLETED":
                print(f"\n✓ Текущий парсинг завершен за {elapsed} сек")
                break
            elif status == "FAILED":
                print(f"\n✗ Текущий парсинг завершился с ошибкой")
                break
        else:
            print(f"\n⚠️  HTTP {resp.status_code}")
            break
    except Exception as e:
        print(f"\n⚠️  Ошибка: {e}")
        break
    
    time.sleep(5)

print(f"\n{'='*80}")
print("Запуск нового парсинга с правильными настройками:")
print("  - Область поиска: Страна / общий поиск")
print("  - Города: Санкт-Петербург")
print(f"{'='*80}\n")

# Запускаем новый парсинг
data = {
    "company_name": "Смарт Хоум",
    "company_site": "http://smarthome.spb.ru",
    "source": "both",
    "email": "test@example.com",
    "search_scope": "country",  # Страна / общий поиск
    "cities": "Санкт-Петербург"  # Город для поиска
}

resp = session.post(f"{BASE_URL}/start_parsing", data=data, allow_redirects=True)

if resp.status_code in [200, 302]:
    if "/tasks/" in resp.url:
        new_task_id = resp.url.split("/tasks/")[-1].split("?")[0].split("#")[0].split("&")[0]
        print(f"✓ Новый парсинг запущен!")
        print(f"Task ID: {new_task_id}")
        print(f"URL: {BASE_URL}/tasks/{new_task_id}")
        print(f"\nОжидание завершения...")
        
        max_wait = 600
        start = time.time()
        while time.time() - start < max_wait:
            try:
                resp = session.get(f"{BASE_URL}/tasks/{new_task_id}/status", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")
                    elapsed = int(time.time() - start)
                    progress = data.get("progress", "")
                    print(f"Статус: {status} | Прогресс: {progress} | Время: {elapsed} сек", end="\r")
                    
                    if status == "COMPLETED":
                        print(f"\n✓ Парсинг завершен за {elapsed} сек")
                        print(f"\nСкачивание отчета...")
                        resp = session.get(f"{BASE_URL}/tasks/{new_task_id}/download-json")
                        if resp.status_code == 200:
                            import json
                            report_data = resp.json()
                            output_file = f"output/verification_report_{new_task_id}.json"
                            os.makedirs("output", exist_ok=True)
                            with open(output_file, "w", encoding="utf-8") as f:
                                json.dump(report_data, f, ensure_ascii=False, indent=2)
                            print(f"✓ Отчет сохранен: {output_file}")
                            
                            # Проверка результатов
                            print(f"\n{'='*80}")
                            print("ПРОВЕРКА РЕЗУЛЬТАТОВ")
                            print(f"{'='*80}")
                            
                            cards = report_data.get("cards", [])
                            statistics = report_data.get("statistics", {})
                            
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
                                        print(f"    - card_reviews_count != aggregated_reviews_count")
                                    if detailed_count != stat_reviews:
                                        print(f"    - детальных отзывов != aggregated_reviews_count")
                            
                            print(f"\n{'='*80}")
                            print("ОТКРОЙТЕ URL В БРАУЗЕРЕ И СРАВНИТЕ ДАННЫЕ")
                            print(f"{'='*80}")
                            for card in cards:
                                print(f"\n{card.get('source', 'unknown').upper()}: {card.get('card_url', 'N/A')}")
                        break
                    elif status == "FAILED":
                        print(f"\n✗ Ошибка: {data.get('error', 'Unknown error')}")
                        break
            except Exception as e:
                print(f"\n⚠️  Ошибка: {e}")
                break
            
            time.sleep(5)
    else:
        print(f"✗ Не удалось получить task_id из ответа")
        print(f"URL: {resp.url}")
else:
    print(f"✗ Ошибка запуска парсинга: {resp.status_code}")

