#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Проверка данных Победа digital на реальных страницах"""

import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.config.settings import Settings

settings = Settings()

def setup_driver():
    """Настройка Selenium драйвера"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    chrome_driver_path = getattr(settings, 'chrome_driver_path', None)
    if chrome_driver_path and os.path.exists(chrome_driver_path):
        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    
    return driver

def check_yandex_card(driver, url, expected_data):
    """Проверка карточки Yandex"""
    print(f"\n{'='*80}")
    print(f"ПРОВЕРКА YANDEX: {expected_data.get('name', 'N/A')}")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Ожидаемые данные из отчета:")
    print(f"  Отзывов: {expected_data.get('reviews_count', 'N/A')}")
    print(f"  Рейтинг: {expected_data.get('rating', 'N/A')}")
    print(f"  С ответами: {expected_data.get('answered', 'N/A')}")
    
    try:
        driver.get(url)
        time.sleep(5)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        results = {
            'reviews_count': None,
            'rating': None,
            'answered_count': None,
            'status': 'success'
        }
        
        # Поиск количества отзывов
        review_selectors = [
            '.tabs-select-view__title._name_reviews .tabs-select-view__counter',
            '.business-header-rating-view__text',
            '[class*="review"] [class*="count"]'
        ]
        
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        potential_count = int(numbers[0])
                        if 1 < potential_count < 1000:
                            results['reviews_count'] = potential_count
                            print(f"  ✓ Найдено количество отзывов: {potential_count} (селектор: {selector})")
                            break
                if results['reviews_count']:
                    break
            except:
                continue
        
        # Поиск рейтинга
        rating_selectors = [
            '.business-header-rating-view__rating',
            '[itemprop="ratingValue"]',
            '[class*="rating"]'
        ]
        
        for selector in rating_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    rating_match = re.search(r'(\d+[.,]\d+)', text)
                    if rating_match:
                        results['rating'] = float(rating_match.group(1).replace(',', '.'))
                        print(f"  ✓ Найден рейтинг: {results['rating']} (селектор: {selector})")
                        break
                if results['rating']:
                    break
            except:
                continue
        
        # Сравнение
        print(f"\nСРАВНЕНИЕ С ОТЧЕТОМ:")
        issues = []
        
        if results['reviews_count']:
            expected = expected_data.get('reviews_count', 0)
            if results['reviews_count'] == expected:
                print(f"  ✅ Отзывов: {results['reviews_count']} (соответствует отчету)")
            else:
                print(f"  ⚠️  Отзывов: {results['reviews_count']} (в отчете: {expected}, разница: {abs(results['reviews_count'] - expected)})")
                issues.append(f"Количество отзывов: найдено {results['reviews_count']}, ожидалось {expected}")
        else:
            print(f"  ⚠️  Не удалось извлечь количество отзывов")
            issues.append("Не удалось извлечь количество отзывов")
        
        if results['rating']:
            expected_rating = float(str(expected_data.get('rating', '0')).replace(',', '.'))
            if abs(results['rating'] - expected_rating) < 0.1:
                print(f"  ✅ Рейтинг: {results['rating']} (соответствует отчету)")
            else:
                print(f"  ⚠️  Рейтинг: {results['rating']} (в отчете: {expected_rating}, разница: {abs(results['rating'] - expected_rating)})")
                issues.append(f"Рейтинг: найден {results['rating']}, ожидался {expected_rating}")
        else:
            print(f"  ⚠️  Не удалось извлечь рейтинг")
            issues.append("Не удалось извлечь рейтинг")
        
        results['issues'] = issues
        return results
        
    except Exception as e:
        print(f"  ✗ Ошибка: {e}")
        return {'status': 'error', 'error': str(e)}

def check_2gis_card(driver, url, expected_data):
    """Проверка карточки 2GIS"""
    print(f"\n{'='*80}")
    print(f"ПРОВЕРКА 2GIS: {expected_data.get('name', 'N/A')}")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Ожидаемые данные из отчета:")
    print(f"  Отзывов: {expected_data.get('reviews_count', 'N/A')}")
    print(f"  Рейтинг: {expected_data.get('rating', 'N/A')}")
    print(f"  С ответами: {expected_data.get('answered', 'N/A')}")
    
    try:
        driver.get(url)
        time.sleep(5)
        
        for i in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        results = {
            'reviews_count': None,
            'rating': None,
            'answered_count': None,
            'status': 'success'
        }
        
        # Поиск количества отзывов
        review_selectors = [
            'span._1xhlznaa',
            'span[class*="_1xhlznaa"]',
            'h2._12jewu69 a._rdxuhv3 span._1xhlznaa'
        ]
        
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text.isdigit():
                        potential_count = int(text)
                        if 1 < potential_count < 1000:
                            results['reviews_count'] = potential_count
                            print(f"  ✓ Найдено количество отзывов: {potential_count} (селектор: {selector})")
                            break
                if results['reviews_count']:
                    break
            except:
                continue
        
        # Поиск рейтинга
        try:
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            rating_match = re.search(r'(\d+[.,]\d+)\s*(?:звезд|star|⭐)', page_text, re.IGNORECASE)
            if rating_match:
                results['rating'] = float(rating_match.group(1).replace(',', '.'))
                print(f"  ✓ Найден рейтинг: {results['rating']}")
        except:
            pass
        
        # Сравнение
        print(f"\nСРАВНЕНИЕ С ОТЧЕТОМ:")
        issues = []
        
        if results['reviews_count']:
            expected = expected_data.get('reviews_count', 0)
            if results['reviews_count'] == expected:
                print(f"  ✅ Отзывов: {results['reviews_count']} (соответствует отчету)")
            else:
                print(f"  ⚠️  Отзывов: {results['reviews_count']} (в отчете: {expected}, разница: {abs(results['reviews_count'] - expected)})")
                issues.append(f"Количество отзывов: найдено {results['reviews_count']}, ожидалось {expected}")
        else:
            print(f"  ⚠️  Не удалось извлечь количество отзывов")
            issues.append("Не удалось извлечь количество отзывов")
        
        if results['rating']:
            expected_rating = float(str(expected_data.get('rating', '0')).replace(',', '.'))
            if abs(results['rating'] - expected_rating) < 0.1:
                print(f"  ✅ Рейтинг: {results['rating']} (соответствует отчету)")
            else:
                print(f"  ⚠️  Рейтинг: {results['rating']} (в отчете: {expected_rating}, разница: {abs(results['rating'] - expected_rating)})")
                issues.append(f"Рейтинг: найден {results['rating']}, ожидался {expected_rating}")
        else:
            print(f"  ⚠️  Не удалось извлечь рейтинг")
            issues.append("Не удалось извлечь рейтинг")
        
        results['issues'] = issues
        return results
        
    except Exception as e:
        print(f"  ✗ Ошибка: {e}")
        return {'status': 'error', 'error': str(e)}

def main():
    report_file = "output/verification_report_45b41463-c624-436d-8600-89c79b8f552f.json"
    
    if not os.path.exists(report_file):
        print(f"Файл отчета не найден: {report_file}")
        return
    
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    print("="*80)
    print("ПРОВЕРКА ДАННЫХ ПОБЕДА DIGITAL НА РЕАЛЬНЫХ СТРАНИЦАХ")
    print("="*80)
    
    cards = report_data.get('cards', [])
    
    driver = None
    try:
        print("\nИнициализация браузера...")
        driver = setup_driver()
        print("✓ Браузер инициализирован")
        
        all_results = []
        
        for card in cards:
            source = card.get('source', 'unknown')
            card_url = card.get('card_url', 'N/A')
            card_name = card.get('card_name', 'N/A')
            
            if card_url == 'N/A':
                print(f"\n⚠️  {source.upper()}: URL карточки отсутствует")
                continue
            
            expected_data = {
                'name': card_name,
                'reviews_count': card.get('card_reviews_count', 0),
                'rating': card.get('card_rating', 'N/A'),
                'answered': card.get('card_answered_reviews_count', 0)
            }
            
            if source == 'yandex':
                result = check_yandex_card(driver, card_url, expected_data)
                all_results.append(('yandex', card_name, result))
            elif source == '2gis':
                result = check_2gis_card(driver, card_url, expected_data)
                all_results.append(('2gis', card_name, result))
        
        # Итоговый отчет
        print(f"\n{'='*80}")
        print("ИТОГОВЫЙ ОТЧЕТ")
        print(f"{'='*80}")
        
        all_issues = []
        for source, name, result in all_results:
            if result.get('status') == 'success':
                issues = result.get('issues', [])
                if issues:
                    all_issues.extend([f"{source.upper()} ({name}): {issue}" for issue in issues])
        
        if all_issues:
            print(f"\n⚠️  Найдено несоответствий: {len(all_issues)}")
            for issue in all_issues:
                print(f"  - {issue}")
        else:
            print(f"\n✅ Все данные соответствуют отчету!")
        
        print(f"\n{'='*80}")
        print("РЕКОМЕНДАЦИИ")
        print(f"{'='*80}")
        print("Для полной проверки откройте URL в браузере и проверьте:")
        print("1. Общее количество отзывов")
        print("2. Рейтинг карточки")
        print("3. Количество отзывов с ответами")
        print("4. Классификацию по рейтингам (положительные/отрицательные/нейтральные)")
        print("5. Детальные данные отзывов (при раскрытии карточки)")
        
    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("\n✓ Браузер закрыт")

if __name__ == "__main__":
    main()

