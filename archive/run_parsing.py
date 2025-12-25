#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
import time
import os

BASE_URL = "http://localhost:8000"
password = os.getenv("SITE_PASSWORD", "admin123")

# Используем сессию для сохранения cookies
session = requests.Session()

print("Авторизация...")
# Сначала получаем страницу логина для установки сессии
session.get(f"{BASE_URL}/login")
# Затем отправляем пароль
resp = session.post(f"{BASE_URL}/login", data={"password": password}, allow_redirects=True)
if resp.status_code in [200, 302]:
    # Проверяем, что мы перенаправлены на главную (не остались на /login)
    if "login" not in resp.url.lower() or resp.url.endswith("/"):
        print("✓ Авторизация успешна")
    else:
        # Проверяем cookies
        if session.cookies:
            print(f"✓ Авторизация успешна (cookies установлены: {list(session.cookies.keys())})")
        else:
            print(f"✗ Ошибка авторизации: не установлена сессия")
            print(f"URL после логина: {resp.url}")
            exit(1)
else:
    print(f"✗ Ошибка авторизации: {resp.status_code}")
    print(f"Ответ: {resp.text[:200]}")
    exit(1)

print("\nЗапуск парсинга...")
data = {
    "company_name": "Смарт Хоум",
    "company_site": "http://smarthome.spb.ru",
    "source": "both",
    "email": "test@example.com",
    "search_scope": "country",  # Страна / общий поиск
    "cities": "Санкт-Петербург"  # Город для поиска
}
resp = session.post(f"{BASE_URL}/start_parsing", data=data, allow_redirects=True)
print(f"Статус ответа: {resp.status_code}")
print(f"URL после запроса: {resp.url}")

# Если редирект на страницу задачи, извлекаем task_id из URL
if resp.status_code in [200, 302]:
    # Проверяем, есть ли редирект на /tasks/{task_id}
    if "/tasks/" in resp.url:
        task_id = resp.url.split("/tasks/")[-1].split("?")[0].split("#")[0].split("&")[0]
        print(f"✓ Task ID из URL: {task_id}")
    # Также проверяем параметр active_task_id в URL
    elif "active_task_id=" in resp.url:
        import urllib.parse
        parsed = urllib.parse.urlparse(resp.url)
        params = urllib.parse.parse_qs(parsed.query)
        if "active_task_id" in params:
            task_id = params["active_task_id"][0]
            print(f"✓ Task ID из параметра: {task_id}")
    else:
        # Пробуем из JSON
        try:
            result = resp.json()
            task_id = result.get("task_id")
            if task_id:
                print(f"✓ Task ID из JSON: {task_id}")
            else:
                print("✗ Task ID не найден в ответе")
                print(f"Ответ: {resp.text[:500]}")
                task_id = None
        except:
            print("✗ Ошибка парсинга JSON, но возможно это редирект")
            print(f"Ответ: {resp.text[:500]}")
            task_id = None
else:
    print(f"✗ Ошибка: {resp.status_code}")
    print(resp.text[:500])
    task_id = None

if not task_id:
    print("Не удалось получить task_id. Выход.")
    exit(1)

print("\nОжидание завершения...")
print(f"URL задачи: {BASE_URL}/tasks/{task_id}")
max_wait = 600
start = time.time()
while time.time() - start < max_wait:
    # Пробуем получить JSON через API или парсим HTML
    try:
        # Используем endpoint /tasks/{task_id}/status для получения JSON
        resp = session.get(f"{BASE_URL}/tasks/{task_id}/status")
        if resp.status_code == 200:
            data = resp.json()
        else:
            # Fallback: пробуем получить HTML и извлечь данные
            resp = session.get(f"{BASE_URL}/tasks/{task_id}")
            if resp.status_code == 200:
                # Ищем taskData в HTML
                import re
                match = re.search(r'var\s+taskData\s*=\s*({.+?});', resp.text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                else:
                    print(f"\n✗ Не удалось получить статус задачи (HTML не содержит taskData)")
                    break
            else:
                print(f"\n✗ Не удалось получить статус задачи (HTTP {resp.status_code})")
                break
        status = data.get("status")
        elapsed = int(time.time() - start)
        print(f"Статус: {status} ({elapsed} сек)", end="\r")
        
        if status == "COMPLETED":
            print(f"\n✓ Завершено за {elapsed} сек")
            break
        elif status == "FAILED":
            print(f"\n✗ Ошибка: {data.get('error', 'Unknown error')}")
            break
    except Exception as e:
        print(f"\n✗ Ошибка при получении статуса: {e}")
        break
    
    time.sleep(5)

if status != "COMPLETED":
    print(f"\n⚠️  Парсинг не завершен (статус: {status})")
    print("Попробуйте проверить статус вручную по URL выше")
    exit(1)

print("\nСкачивание отчета...")
resp = session.get(f"{BASE_URL}/tasks/{task_id}/download-json")
if resp.status_code != 200:
    print(f"✗ Ошибка получения отчета: {resp.status_code}")
    exit(1)
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

print("\n" + "="*80)
print("ОТКРОЙТЕ URL В БРАУЗЕРЕ И СРАВНИТЕ ДАННЫЕ")
print("="*80)
for card in cards:
    print(f"\n{card.get('source', 'unknown').upper()}: {card.get('card_url', 'N/A')}")

