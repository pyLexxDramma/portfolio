#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для проверки соответствия данных в отчетах реальным страницам"""

import json
import sys
import os

def verify_data_consistency(json_file):
    """Проверяет согласованность данных в отчете"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("ПРОВЕРКА СООТВЕТСТВИЯ ДАННЫХ В ОТЧЕТАХ")
    print("=" * 80)
    
    stats = data.get('statistics', {})
    cards = data.get('cards', [])
    
    issues = []
    
    # Проверка 1: Соответствие статистики и карточек
    print("\n1. ПРОВЕРКА СООТВЕТСТВИЯ СТАТИСТИКИ И КАРТОЧЕК")
    print("-" * 80)
    
    for source in ['yandex', '2gis']:
        if source not in stats:
            continue
            
        source_cards = [c for c in cards if c.get('source') == source]
        stat = stats[source]
        
        print(f"\n{source.upper()}:")
        print(f"  Статистика: карточек = {stat.get('total_cards_found', 0)}")
        print(f"  Фактически карточек в отчете: {len(source_cards)}")
        
        if stat.get('total_cards_found', 0) != len(source_cards):
            issues.append(f"{source}: Несоответствие количества карточек: статистика={stat.get('total_cards_found', 0)}, фактически={len(source_cards)}")
        
        # Проверка по каждой карточке
        for i, card in enumerate(source_cards, 1):
            print(f"\n  Карточка {i}: {card.get('card_name', 'N/A')[:50]}")
            
            # Проверка количества отзывов
            card_reviews = card.get('card_reviews_count', 0)
            stat_reviews = stat.get('aggregated_reviews_count', 0)
            
            print(f"    Отзывов в карточке: {card_reviews}")
            print(f"    Отзывов в статистике: {stat_reviews}")
            
            if card_reviews != stat_reviews:
                issues.append(f"{source} карточка {i}: Несоответствие отзывов: карточка={card_reviews}, статистика={stat_reviews}")
            
            # Проверка рейтинга
            card_rating = card.get('card_rating', '')
            stat_rating = stat.get('aggregated_rating', 0)
            print(f"    Рейтинг в карточке: {card_rating}")
            print(f"    Рейтинг в статистике: {stat_rating}")
            
            # Проверка положительных/отрицательных
            card_pos = card.get('card_reviews_positive', 0)
            card_neg = card.get('card_reviews_negative', 0)
            card_neut = card.get('card_reviews_neutral', 0)
            stat_pos = stat.get('aggregated_positive_reviews', 0)
            stat_neg = stat.get('aggregated_negative_reviews', 0)
            stat_neut = stat.get('aggregated_neutral_reviews', 0)
            
            print(f"    Положительных: карточка={card_pos}, статистика={stat_pos}")
            print(f"    Отрицательных: карточка={card_neg}, статистика={stat_neg}")
            print(f"    Нейтральных: карточка={card_neut}, статистика={stat_neut}")
            
            total_card = card_pos + card_neg + card_neut
            total_stat = stat_pos + stat_neg + stat_neut
            
            if total_card != total_stat:
                issues.append(f"{source} карточка {i}: Несоответствие суммы отзывов: карточка={total_card}, статистика={total_stat}")
            
            # Проверка ответов
            card_answered = card.get('card_answered_reviews_count', 0)
            card_unanswered = card.get('card_unanswered_reviews_count', 0)
            stat_answered = stat.get('aggregated_answered_reviews_count', 0)
            stat_unanswered = stat.get('aggregated_unanswered_reviews_count', 0)
            
            print(f"    С ответами: карточка={card_answered}, статистика={stat_answered}")
            print(f"    Без ответов: карточка={card_unanswered}, статистика={stat_unanswered}")
            
            if card_answered != stat_answered:
                issues.append(f"{source} карточка {i}: Несоответствие ответов: карточка={card_answered}, статистика={stat_answered}")
            
            # Проверка детальных отзывов
            detailed_reviews = card.get('detailed_reviews', [])
            print(f"    Детальных отзывов в JSON: {len(detailed_reviews)}")
            
            if len(detailed_reviews) != card_reviews:
                issues.append(f"{source} карточка {i}: Несоответствие детальных отзывов: card_reviews_count={card_reviews}, detailed_reviews={len(detailed_reviews)}")
            
            # Проверка наличия URL
            if 'card_url' not in card and 'url' not in card:
                issues.append(f"{source} карточка {i}: URL карточки отсутствует в отчете")
    
    # Проверка 2: Combined статистика
    print("\n2. ПРОВЕРКА COMBINED СТАТИСТИКИ")
    print("-" * 80)
    
    if 'combined' in stats:
        combined = stats['combined']
        yandex = stats.get('yandex', {})
        gis = stats.get('2gis', {})
        
        print(f"Combined карточек: {combined.get('total_cards_found', 0)}")
        print(f"Yandex + 2GIS: {yandex.get('total_cards_found', 0) + gis.get('total_cards_found', 0)}")
        
        if combined.get('total_cards_found', 0) != yandex.get('total_cards_found', 0) + gis.get('total_cards_found', 0):
            issues.append(f"Combined: Несоответствие карточек")
        
        print(f"Combined отзывов: {combined.get('aggregated_reviews_count', 0)}")
        print(f"Yandex + 2GIS: {yandex.get('aggregated_reviews_count', 0) + gis.get('aggregated_reviews_count', 0)}")
        
        if combined.get('aggregated_reviews_count', 0) != yandex.get('aggregated_reviews_count', 0) + gis.get('aggregated_reviews_count', 0):
            issues.append(f"Combined: Несоответствие отзывов")
    
    # Итоги
    print("\n" + "=" * 80)
    print("ИТОГИ ПРОВЕРКИ")
    print("=" * 80)
    
    if issues:
        print(f"\nНАЙДЕНО ПРОБЛЕМ: {len(issues)}")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("\n✓ Проблем не обнаружено")
    
    return issues

if __name__ == "__main__":
    json_file = "output/report_company_88d3b01e_with_answers.json"
    if os.path.exists(json_file):
        verify_data_consistency(json_file)
    else:
        print(f"Файл {json_file} не найден!")
        sys.exit(1)

