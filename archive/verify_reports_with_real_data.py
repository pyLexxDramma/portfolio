#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для проверки соответствия данных в отчетах реальным страницам"""

import json
import sys
import os
import re

def extract_card_urls(json_file):
    """Извлекает URL карточек из JSON отчета"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cards = data.get('cards', [])
    urls = {}
    
    for i, card in enumerate(cards, 1):
        source = card.get('source', 'unknown')
        card_name = card.get('card_name', 'N/A')
        card_url = card.get('card_url') or card.get('url', 'N/A')
        
        if card_url != 'N/A':
            urls[f"{source}_{i}"] = {
                'name': card_name,
                'url': card_url,
                'source': source,
                'card_data': card
            }
        else:
            print(f"⚠️  Карточка {i} ({source}): URL не найден!")
    
    return urls, data

def analyze_card_data(card, source):
    """Анализирует данные карточки"""
    print(f"\n{'='*80}")
    print(f"КАРТОЧКА: {card.get('card_name', 'N/A')} ({source.upper()})")
    print(f"{'='*80}")
    
    if card.get('card_url'):
        print(f"URL: {card.get('card_url')}")
    else:
        print("⚠️  URL: ОТСУТСТВУЕТ")
    
    print(f"\nОсновные данные:")
    print(f"  Название: {card.get('card_name', 'N/A')}")
    print(f"  Адрес: {card.get('card_address', 'N/A')}")
    print(f"  Рейтинг: {card.get('card_rating', 'N/A')}")
    print(f"  Сайт: {card.get('card_website', 'N/A')}")
    print(f"  Телефон: {card.get('card_phone', 'N/A')}")
    
    print(f"\nОтзывы:")
    print(f"  Всего отзывов: {card.get('card_reviews_count', 0)}")
    print(f"  Положительных: {card.get('card_reviews_positive', 0)}")
    print(f"  Отрицательных: {card.get('card_reviews_negative', 0)}")
    print(f"  Нейтральных: {card.get('card_reviews_neutral', 0)}")
    print(f"  С ответами: {card.get('card_answered_reviews_count', 0)}")
    print(f"  Без ответов: {card.get('card_unanswered_reviews_count', 0)}")
    
    # Проверка согласованности
    total_by_rating = (card.get('card_reviews_positive', 0) + 
                      card.get('card_reviews_negative', 0) + 
                      card.get('card_reviews_neutral', 0))
    total_reviews = card.get('card_reviews_count', 0)
    
    print(f"\nПроверка согласованности:")
    print(f"  Сумма по рейтингам: {total_by_rating}")
    print(f"  Всего отзывов: {total_reviews}")
    if total_by_rating != total_reviews:
        print(f"  ⚠️  НЕСООТВЕТСТВИЕ: {abs(total_by_rating - total_reviews)} отзывов")
    else:
        print(f"  ✓ Соответствует")
    
    answered = card.get('card_answered_reviews_count', 0)
    unanswered = card.get('card_unanswered_reviews_count', 0)
    total_answered = answered + unanswered
    
    print(f"  С ответами + Без ответов: {total_answered}")
    if total_answered != total_reviews:
        print(f"  ⚠️  НЕСООТВЕТСТВИЕ: {abs(total_answered - total_reviews)} отзывов")
    else:
        print(f"  ✓ Соответствует")
    
    # Детальные отзывы
    detailed_reviews = card.get('detailed_reviews', [])
    print(f"\nДетальные отзывы:")
    print(f"  Количество в JSON: {len(detailed_reviews)}")
    if len(detailed_reviews) != total_reviews:
        print(f"  ⚠️  НЕСООТВЕТСТВИЕ: ожидалось {total_reviews}, найдено {len(detailed_reviews)}")
    else:
        print(f"  ✓ Соответствует")
    
    # Проверка детальных отзывов
    if detailed_reviews:
        detailed_positive = sum(1 for r in detailed_reviews if isinstance(r, dict) and r.get('review_rating', 0) >= 4)
        detailed_negative = sum(1 for r in detailed_reviews if isinstance(r, dict) and r.get('review_rating', 0) in (1, 2))
        detailed_neutral = sum(1 for r in detailed_reviews if isinstance(r, dict) and r.get('review_rating', 0) == 3)
        detailed_answered = sum(1 for r in detailed_reviews if isinstance(r, dict) and r.get('has_response', False))
        
        print(f"\nПроверка детальных отзывов:")
        print(f"  Положительных в детальных: {detailed_positive} (ожидалось: {card.get('card_reviews_positive', 0)})")
        print(f"  Отрицательных в детальных: {detailed_negative} (ожидалось: {card.get('card_reviews_negative', 0)})")
        print(f"  Нейтральных в детальных: {detailed_neutral} (ожидалось: {card.get('card_reviews_neutral', 0)})")
        print(f"  С ответами в детальных: {detailed_answered} (ожидалось: {card.get('card_answered_reviews_count', 0)})")
        
        issues = []
        if detailed_positive != card.get('card_reviews_positive', 0):
            issues.append(f"Положительные: {detailed_positive} vs {card.get('card_reviews_positive', 0)}")
        if detailed_negative != card.get('card_reviews_negative', 0):
            issues.append(f"Отрицательные: {detailed_negative} vs {card.get('card_reviews_negative', 0)}")
        if detailed_neutral != card.get('card_reviews_neutral', 0):
            issues.append(f"Нейтральные: {detailed_neutral} vs {card.get('card_reviews_neutral', 0)}")
        if detailed_answered != card.get('card_answered_reviews_count', 0):
            issues.append(f"С ответами: {detailed_answered} vs {card.get('card_answered_reviews_count', 0)}")
        
        if issues:
            print(f"  ⚠️  НЕСООТВЕТСТВИЯ:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print(f"  ✓ Все соответствует")

def compare_with_statistics(cards, statistics):
    """Сравнивает данные карточек со статистикой"""
    print(f"\n{'='*80}")
    print("СРАВНЕНИЕ С АГРЕГИРОВАННОЙ СТАТИСТИКОЙ")
    print(f"{'='*80}")
    
    for source in ['yandex', '2gis']:
        if source not in statistics:
            continue
        
        source_cards = [c for c in cards if c.get('source') == source]
        stat = statistics[source]
        
        print(f"\n{source.upper()}:")
        print(f"  Статистика: карточек = {stat.get('total_cards_found', 0)}")
        print(f"  Фактически: {len(source_cards)}")
        
        if len(source_cards) == 0:
            continue
        
        # Берем первую карточку (обычно одна)
        card = source_cards[0]
        
        print(f"\n  Сравнение данных карточки и статистики:")
        print(f"    Отзывов:")
        print(f"      Карточка: {card.get('card_reviews_count', 0)}")
        print(f"      Статистика: {stat.get('aggregated_reviews_count', 0)}")
        if card.get('card_reviews_count', 0) != stat.get('aggregated_reviews_count', 0):
            print(f"      ⚠️  НЕСООТВЕТСТВИЕ")
        else:
            print(f"      ✓ Соответствует")
        
        print(f"    Рейтинг:")
        print(f"      Карточка: {card.get('card_rating', 'N/A')}")
        print(f"      Статистика: {stat.get('aggregated_rating', 0)}")
        
        print(f"    Положительных:")
        print(f"      Карточка: {card.get('card_reviews_positive', 0)}")
        print(f"      Статистика: {stat.get('aggregated_positive_reviews', 0)}")
        if card.get('card_reviews_positive', 0) != stat.get('aggregated_positive_reviews', 0):
            print(f"      ⚠️  НЕСООТВЕТСТВИЕ")
        else:
            print(f"      ✓ Соответствует")
        
        print(f"    Отрицательных:")
        print(f"      Карточка: {card.get('card_reviews_negative', 0)}")
        print(f"      Статистика: {stat.get('aggregated_negative_reviews', 0)}")
        if card.get('card_reviews_negative', 0) != stat.get('aggregated_negative_reviews', 0):
            print(f"      ⚠️  НЕСООТВЕТСТВИЕ")
        else:
            print(f"      ✓ Соответствует")
        
        print(f"    С ответами:")
        print(f"      Карточка: {card.get('card_answered_reviews_count', 0)}")
        print(f"      Статистика: {stat.get('aggregated_answered_reviews_count', 0)}")
        if card.get('card_answered_reviews_count', 0) != stat.get('aggregated_answered_reviews_count', 0):
            print(f"      ⚠️  НЕСООТВЕТСТВИЕ")
        else:
            print(f"      ✓ Соответствует")

def main():
    # Ищем последний JSON отчет
    json_files = [f for f in os.listdir("output") if f.endswith("_with_answers.json")]
    if not json_files:
        print("JSON отчеты не найдены в папке output!")
        sys.exit(1)
    
    # Берем последний по времени изменения
    json_files_with_time = [(f, os.path.getmtime(os.path.join("output", f))) for f in json_files]
    json_files_with_time.sort(key=lambda x: x[1], reverse=True)
    json_file = os.path.join("output", json_files_with_time[0][0])
    
    print(f"Используется отчет: {json_file}")
    
    print("="*80)
    print("ПРОВЕРКА СООТВЕТСТВИЯ ДАННЫХ В ОТЧЕТАХ РЕАЛЬНЫМ СТРАНИЦАМ")
    print("="*80)
    
    urls, data = extract_card_urls(json_file)
    
    print(f"\nНайдено карточек с URL: {len(urls)}")
    for key, info in urls.items():
        print(f"  {key}: {info['name'][:50]} - {info['url']}")
    
    cards = data.get('cards', [])
    statistics = data.get('statistics', {})
    
    # Анализ каждой карточки
    for card in cards:
        source = card.get('source', 'unknown')
        analyze_card_data(card, source)
    
    # Сравнение со статистикой
    compare_with_statistics(cards, statistics)
    
    # Итоговый отчет
    print(f"\n{'='*80}")
    print("ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*80}")
    print(f"\nURL карточек для проверки на реальных страницах:")
    for key, info in urls.items():
        print(f"\n{key.upper()}:")
        print(f"  Название: {info['name']}")
        print(f"  URL: {info['url']}")
        print(f"  Источник: {info['source']}")
        print(f"\n  Для проверки откройте URL в браузере и сравните:")
        print(f"    - Рейтинг карточки")
        print(f"    - Количество отзывов")
        print(f"    - Количество положительных/отрицательных/нейтральных")
        print(f"    - Количество ответов организации")
        print(f"    - Детальные данные отзывов")

if __name__ == "__main__":
    main()

