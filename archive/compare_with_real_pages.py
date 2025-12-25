#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Сравнение данных из отчета с реальными страницами"""

import json
import os
import requests
from bs4 import BeautifulSoup
import re

def extract_yandex_data(url):
    """Попытка извлечь данные со страницы Yandex"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Попытка найти количество отзывов
            reviews_count = None
            rating = None
            
            # Ищем в различных местах
            review_selectors = [
                '.business-header-rating-view__text',
                '.tabs-select-view__counter',
                '[class*="review"]',
                '[class*="отзыв"]'
            ]
            
            for selector in review_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text()
                    # Ищем числа в тексте
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        potential_count = int(numbers[0])
                        if 50 < potential_count < 500:  # Разумные пределы
                            reviews_count = potential_count
                            break
                if reviews_count:
                    break
            
            # Ищем рейтинг
            rating_selectors = [
                '.business-header-rating-view__rating',
                '[class*="rating"]',
                '[itemprop="ratingValue"]'
            ]
            
            for selector in rating_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text()
                    rating_match = re.search(r'(\d+[.,]\d+)', text)
                    if rating_match:
                        rating = float(rating_match.group(1).replace(',', '.'))
                        break
                if rating:
                    break
            
            return {
                'reviews_count': reviews_count,
                'rating': rating,
                'status': 'success' if reviews_count or rating else 'partial'
            }
    except Exception as e:
        return {'error': str(e), 'status': 'error'}
    
    return {'status': 'failed'}

def extract_2gis_data(url):
    """Попытка извлечь данные со страницы 2GIS"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            reviews_count = None
            rating = None
            
            # Ищем количество отзывов
            review_text = soup.get_text()
            # Ищем паттерны типа "319 отзывов" или "319 отзыв"
            review_match = re.search(r'(\d+)\s*(?:отзыв|отзывов|отзывa)', review_text, re.IGNORECASE)
            if review_match:
                reviews_count = int(review_match.group(1))
            
            # Ищем рейтинг
            rating_match = re.search(r'(\d+[.,]\d+)\s*(?:звезд|звёзд|★|⭐)', review_text)
            if rating_match:
                rating = float(rating_match.group(1).replace(',', '.'))
            
            return {
                'reviews_count': reviews_count,
                'rating': rating,
                'status': 'success' if reviews_count or rating else 'partial'
            }
    except Exception as e:
        return {'error': str(e), 'status': 'error'}
    
    return {'status': 'failed'}

def main():
    report_file = "output/verification_report_208bc931-92cf-4797-8358-4cd680eeaa9b.json"
    
    if not os.path.exists(report_file):
        print(f"Файл отчета не найден: {report_file}")
        return
    
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    print("="*80)
    print("СРАВНЕНИЕ ДАННЫХ ИЗ ОТЧЕТА С РЕАЛЬНЫМИ СТРАНИЦАМИ")
    print("="*80)
    
    cards = report_data.get('cards', [])
    statistics = report_data.get('statistics', {})
    
    for card in cards:
        source = card.get('source', 'unknown')
        card_name = card.get('card_name', 'N/A')
        card_url = card.get('card_url', 'N/A')
        
        print(f"\n{'='*80}")
        print(f"{source.upper()}: {card_name}")
        print(f"{'='*80}")
        print(f"URL: {card_url}")
        
        if card_url == 'N/A':
            print("⚠️  URL карточки отсутствует в отчете")
            continue
        
        # Данные из отчета
        report_reviews = card.get('card_reviews_count', 0)
        report_rating = card.get('card_rating', 'N/A')
        report_positive = card.get('card_reviews_positive', 0)
        report_negative = card.get('card_reviews_negative', 0)
        report_neutral = card.get('card_reviews_neutral', 0)
        report_answered = card.get('card_answered_reviews_count', 0)
        report_unanswered = card.get('card_unanswered_reviews_count', 0)
        detailed_count = len(card.get('detailed_reviews', []))
        
        print(f"\nДАННЫЕ ИЗ ОТЧЕТА:")
        print(f"  Общее количество отзывов: {report_reviews}")
        print(f"  Рейтинг: {report_rating}")
        print(f"  Положительных: {report_positive}")
        print(f"  Отрицательных: {report_negative}")
        print(f"  Нейтральных: {report_neutral}")
        print(f"  С ответами: {report_answered}")
        print(f"  Без ответов: {report_unanswered}")
        print(f"  Детальных отзывов в JSON: {detailed_count}")
        
        # Попытка получить данные с реальной страницы
        print(f"\nПОПЫТКА ПОЛУЧИТЬ ДАННЫЕ С РЕАЛЬНОЙ СТРАНИЦЫ...")
        if source == 'yandex':
            real_data = extract_yandex_data(card_url)
        elif source == '2gis':
            real_data = extract_2gis_data(card_url)
        else:
            real_data = {'status': 'unknown_source'}
        
        if real_data.get('status') == 'success' or real_data.get('status') == 'partial':
            print(f"  Данные получены:")
            if real_data.get('reviews_count'):
                print(f"    Количество отзывов на странице: {real_data['reviews_count']}")
                if real_data['reviews_count'] == report_reviews:
                    print(f"    ✅ СООТВЕТСТВУЕТ отчету")
                else:
                    print(f"    ⚠️  НЕСООТВЕТСТВИЕ: отчет={report_reviews}, страница={real_data['reviews_count']}")
            else:
                print(f"    ⚠️  Не удалось извлечь количество отзывов")
            
            if real_data.get('rating'):
                print(f"    Рейтинг на странице: {real_data['rating']}")
                report_rating_float = float(str(report_rating).replace(',', '.'))
                if abs(real_data['rating'] - report_rating_float) < 0.1:
                    print(f"    ✅ СООТВЕТСТВУЕТ отчету")
                else:
                    print(f"    ⚠️  НЕСООТВЕТСТВИЕ: отчет={report_rating}, страница={real_data['rating']}")
            else:
                print(f"    ⚠️  Не удалось извлечь рейтинг")
        elif real_data.get('status') == 'error':
            print(f"  ⚠️  Ошибка при получении данных: {real_data.get('error', 'Unknown error')}")
        else:
            print(f"  ⚠️  Не удалось получить данные со страницы (возможно, требуется JavaScript)")
        
        print(f"\n📋 РУЧНАЯ ПРОВЕРКА:")
        print(f"  Откройте URL в браузере: {card_url}")
        print(f"  Проверьте:")
        print(f"    1. Общее количество отзывов (ожидается: {report_reviews})")
        print(f"    2. Рейтинг карточки (ожидается: {report_rating})")
        print(f"    3. Количество отзывов с ответами (ожидается: {report_answered})")
        print(f"    4. Классификация:")
        print(f"       - Положительных: {report_positive}")
        print(f"       - Отрицательных: {report_negative}")
        print(f"       - Нейтральных: {report_neutral}")
        print(f"    5. Откройте несколько отзывов и проверьте:")
        print(f"       - Полноту текста отзыва")
        print(f"       - Наличие ответа организации")
        print(f"       - Дату отзыва и ответа")
        print(f"       - Рейтинг отзыва")
    
    print(f"\n{'='*80}")
    print("ИТОГОВЫЙ СТАТУС")
    print(f"{'='*80}")
    print("Данные из отчета:")
    for card in cards:
        source = card.get('source', 'unknown')
        print(f"  {source.upper()}: {card.get('card_reviews_count', 0)} отзывов, рейтинг {card.get('card_rating', 'N/A')}")
    print("\n⚠️  ВАЖНО: Для полной проверки необходимо открыть URL в браузере,")
    print("   так как многие данные требуют JavaScript для отображения.")

if __name__ == "__main__":
    main()

