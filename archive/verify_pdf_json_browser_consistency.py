#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Проверка соответствия данных между PDF, JSON и браузером"""

import json
import os
import sys

def verify_consistency(task_id):
    """Проверяет соответствие данных между JSON отчетом и данными задачи"""
    
    # Загружаем JSON отчет
    json_file = f"output/report_{task_id}.json"
    if not os.path.exists(json_file):
        print(f"JSON файл не найден: {json_file}")
        return False
    
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    print("="*80)
    print("ПРОВЕРКА СООТВЕТСТВИЯ ДАННЫХ")
    print("="*80)
    
    cards = json_data.get('cards', [])
    statistics = json_data.get('statistics', {})
    
    issues = []
    
    # Проверяем каждую карточку
    for card in cards:
        source = card.get('source', 'unknown')
        card_name = card.get('card_name', 'N/A')
        card_reviews = card.get('card_reviews_count', 0)
        detailed_count = len(card.get('detailed_reviews', []))
        
        # Проверка: количество детальных отзывов должно соответствовать количеству отзывов
        if detailed_count != card_reviews and card_reviews > 0:
            issue = f"{source.upper()} ({card_name}): Количество детальных отзывов ({detailed_count}) != общее количество ({card_reviews})"
            issues.append(issue)
            print(f"⚠️  {issue}")
        
        # Проверка рейтинга
        card_rating = card.get('card_rating', '—')
        if not card_rating or card_rating == '—' or str(card_rating).strip() == '':
            issue = f"{source.upper()} ({card_name}): Рейтинг карточки отсутствует или пустой"
            issues.append(issue)
            print(f"⚠️  {issue}")
    
    # Проверяем статистику
    for source in ['yandex', '2gis', 'combined']:
        if source in statistics:
            stat = statistics[source]
            source_cards = [c for c in cards if c.get('source') == source]
            
            if len(source_cards) > 1:
                # Если несколько карточек, проверяем сумму
                total_card_reviews = sum(c.get('card_reviews_count', 0) for c in source_cards)
                aggregated_reviews = stat.get('aggregated_reviews_count', 0)
                
                if total_card_reviews != aggregated_reviews:
                    issue = f"{source.upper()}: Сумма отзывов по карточкам ({total_card_reviews}) != агрегированное значение ({aggregated_reviews})"
                    issues.append(issue)
                    print(f"⚠️  {issue}")
    
    if issues:
        print(f"\n⚠️  Найдено проблем: {len(issues)}")
        return False
    else:
        print("\n✅ Все данные соответствуют!")
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
    else:
        # Ищем последний JSON файл
        json_files = [f for f in os.listdir("output") if f.startswith("report_") and f.endswith(".json")]
        if not json_files:
            print("Не найдено JSON файлов в папке output")
            sys.exit(1)
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join("output", x)), reverse=True)
        task_id = json_files[0].replace("report_", "").replace(".json", "")
        print(f"Используется последний файл: {json_files[0]}")
    
    verify_consistency(task_id)

