#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для запуска парсинга и проверки результатов"""

import requests
import json
import time
import sys
import os

BASE_URL = "http://localhost:8000"

def login():
    """Авторизация на сервере"""
    password = os.getenv("SITE_PASSWORD", "admin")
    response = requests.post(f"{BASE_URL}/login", data={"password": password})
    if response.status_code == 200:
        cookies = response.cookies
        print("✓ Авторизация успешна")
        return cookies
    else:
        print(f"✗ Ошибка авторизации: {response.status_code}")
        return None

def start_parsing(cookies):
    """Запуск парсинга"""
    data = {
        "company_name": "Смарт Хоум",
        "company_site": "http://smarthome.spb.ru",
        "source": "both"
    }
    
    response = requests.post(f"{BASE_URL}/start", json=data, cookies=cookies)
    if response.status_code == 200:
        result = response.json()
        task_id = result.get("task_id")
        print(f"✓ Парсинг запущен. Task ID: {task_id}")
        return task_id
    else:
        print(f"✗ Ошибка запуска парсинга: {response.status_code}")
        print(response.text)
        return None

def wait_for_completion(task_id, cookies, max_wait=600):
    """Ожидание завершения парсинга"""
    print(f"\nОжидание завершения парсинга (максимум {max_wait} секунд)...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"{BASE_URL}/tasks/{task_id}", cookies=cookies)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            
            if status == "COMPLETED":
                print(f"✓ Парсинг завершен!")
                return data
            elif status == "FAILED":
                print(f"✗ Парсинг завершился с ошибкой")
                return data
            else:
                elapsed = int(time.time() - start_time)
                print(f"  Статус: {status} (прошло {elapsed} сек)", end="\r")
        
        time.sleep(5)
    
    print(f"\n✗ Превышено время ожидания ({max_wait} секунд)")
    return None

def download_json_report(task_id, cookies):
    """Скачивание JSON отчета"""
    response = requests.get(f"{BASE_URL}/tasks/{task_id}/download-json", cookies=cookies)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"✗ Ошибка скачивания JSON: {response.status_code}")
        return None

def verify_report(report_data):
    """Проверка отчета"""
    print("\n" + "="*80)
    print("ПРОВЕРКА РЕЗУЛЬТАТОВ ПАРСИНГА")
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
        
        print(f"  Отзывов в карточке: {card_reviews}")
        print(f"  Отзывов в статистике: {stat_reviews}")
        
        if card_reviews != stat_reviews:
            issues.append(f"{source}: card_reviews_count ({card_reviews}) != aggregated_reviews_count ({stat_reviews})")
            print(f"  ⚠️  НЕСООТВЕТСТВИЕ!")
        else:
            print(f"  ✓ Соответствует")
        
        detailed_reviews = card.get("detailed_reviews", [])
        print(f"  Детальных отзывов: {len(detailed_reviews)}")
        
        if len(detailed_reviews) != stat_reviews:
            issues.append(f"{source}: детальных отзывов ({len(detailed_reviews)}) != aggregated_reviews_count ({stat_reviews})")
            print(f"  ⚠️  НЕСООТВЕТСТВИЕ!")
        else:
            print(f"  ✓ Соответствует")
    
    print("\n" + "="*80)
    if issues:
        print(f"НАЙДЕНО ПРОБЛЕМ: {len(issues)}")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("✓ ВСЕ ДАННЫЕ СООТВЕТСТВУЮТ!")
    
    return issues, cards, statistics

def main():
    print("="*80)
    print("ЗАПУСК ПАРСИНГА И ПРОВЕРКА РЕЗУЛЬТАТОВ")
    print("="*80)
    
    # Авторизация
    cookies = login()
    if not cookies:
        sys.exit(1)
    
    # Запуск парсинга
    task_id = start_parsing(cookies)
    if not task_id:
        sys.exit(1)
    
    # Ожидание завершения
    result = wait_for_completion(task_id, cookies)
    if not result:
        sys.exit(1)
    
    # Скачивание отчета
    print("\nСкачивание JSON отчета...")
    report_data = download_json_report(task_id, cookies)
    if not report_data:
        sys.exit(1)
    
    # Сохранение отчета
    output_file = f"output/verification_report_{task_id}.json"
    os.makedirs("output", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f"✓ Отчет сохранен: {output_file}")
    
    # Проверка
    issues, cards, statistics = verify_report(report_data)
    
    # Вывод URL для проверки
    print("\n" + "="*80)
    print("URL ДЛЯ ПРОВЕРКИ В БРАУЗЕРЕ")
    print("="*80)
    
    for card in cards:
        source = card.get("source", "unknown")
        card_name = card.get("card_name", "N/A")
        card_url = card.get("card_url", "N/A")
        print(f"\n{source.upper()}: {card_name}")
        print(f"  {card_url}")
        print(f"  Проверьте:")
        print(f"    - Рейтинг: {card.get('card_rating', 'N/A')}")
        print(f"    - Отзывов: должно быть {statistics.get(source, {}).get('aggregated_reviews_count', 0)}")
        print(f"    - С ответами: должно быть {statistics.get(source, {}).get('aggregated_answered_reviews_count', 0)}")
    
    print("\n" + "="*80)
    if issues:
        print("⚠️  НАЙДЕНЫ ПРОБЛЕМЫ - ТРЕБУЕТСЯ ПРОВЕРКА В БРАУЗЕРЕ")
    else:
        print("✓ ВСЕ ДАННЫЕ СООТВЕТСТВУЮТ - РЕКОМЕНДУЕТСЯ ПРОВЕРКА В БРАУЗЕРЕ")
    print("="*80)

if __name__ == "__main__":
    main()

