#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для проверки соответствия данных в отчетах реальным страницам"""

import json
import sys
import os

def analyze_json_report(json_file):
    """Анализирует JSON отчет и извлекает информацию о карточках"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print(f"АНАЛИЗ ОТЧЕТА: {json_file}")
    print("=" * 80)
    
    print(f"\nЗадача ID: {data.get('task_id')}")
    print(f"Компания: {data.get('company_name')}")
    print(f"Сайт: {data.get('company_site')}")
    print(f"Источники: {data.get('source')}")
    
    # Статистика
    stats = data.get('statistics', {})
    print("\n--- СТАТИСТИКА ---")
    for source, stat in stats.items():
        print(f"\n{source.upper()}:")
        print(f"  Карточек найдено: {stat.get('total_cards_found', 0)}")
        print(f"  Рейтинг: {stat.get('aggregated_rating', 0)}")
        print(f"  Всего отзывов: {stat.get('aggregated_reviews_count', 0)}")
        print(f"  Положительных: {stat.get('aggregated_positive_reviews', 0)}")
        print(f"  Отрицательных: {stat.get('aggregated_negative_reviews', 0)}")
        print(f"  Нейтральных: {stat.get('aggregated_neutral_reviews', 0)}")
        print(f"  С ответами: {stat.get('aggregated_answered_reviews_count', 0)}")
        print(f"  Без ответов: {stat.get('aggregated_unanswered_reviews_count', 0)}")
    
    # Карточки
    cards = data.get('cards', [])
    print(f"\n--- КАРТОЧКИ (всего {len(cards)}) ---")
    
    for i, card in enumerate(cards, 1):
        print(f"\nКарточка {i}:")
        print(f"  Название: {card.get('card_name', 'N/A')}")
        print(f"  Адрес: {card.get('card_address', 'N/A')}")
        print(f"  Рейтинг: {card.get('card_rating', 'N/A')}")
        print(f"  Отзывов: {card.get('card_reviews_count', 0)}")
        print(f"  Сайт: {card.get('card_website', 'N/A')}")
        print(f"  Телефон: {card.get('card_phone', 'N/A')}")
        print(f"  Положительных: {card.get('card_reviews_positive', 0)}")
        print(f"  Отрицательных: {card.get('card_reviews_negative', 0)}")
        print(f"  Нейтральных: {card.get('card_reviews_neutral', 0)}")
        print(f"  С ответами: {card.get('card_answered_reviews_count', 0)}")
        print(f"  Без ответов: {card.get('card_unanswered_reviews_count', 0)}")
        
        # Проверяем наличие URL
        if 'card_url' in card:
            print(f"  URL: {card.get('card_url')}")
        elif 'url' in card:
            print(f"  URL: {card.get('url')}")
        else:
            print(f"  URL: НЕ НАЙДЕН В ОТЧЕТЕ")
        
        # Детальные отзывы
        detailed_reviews = card.get('detailed_reviews', [])
        print(f"  Детальных отзывов в JSON: {len(detailed_reviews)}")
        
        if detailed_reviews:
            print(f"  Первый отзыв:")
            first_review = detailed_reviews[0]
            print(f"    ID: {first_review.get('review_id', 'N/A')}")
            print(f"    Рейтинг: {first_review.get('review_rating', 'N/A')}")
            print(f"    Автор: {first_review.get('review_author', 'N/A')}")
            print(f"    Дата: {first_review.get('review_date', 'N/A')}")
            print(f"    Есть ответ: {first_review.get('has_response', False)}")
    
    # Cards summary
    cards_summary = data.get('cards_summary', {})
    if cards_summary:
        print(f"\n--- СВОДКА ПО КАРТОЧКАМ ---")
        print(f"  Всего: {cards_summary.get('total', 0)}")
        print(f"  По источникам: {cards_summary.get('by_source', {})}")
    
    return data

if __name__ == "__main__":
    json_file = "output/report_company_88d3b01e_with_answers.json"
    if os.path.exists(json_file):
        analyze_json_report(json_file)
    else:
        print(f"Файл {json_file} не найден!")
        sys.exit(1)

