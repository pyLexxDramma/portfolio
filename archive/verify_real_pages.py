#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Проверка данных на реальных страницах Yandex и 2GIS с помощью Selenium"""

import json
import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.config.settings import Settings

settings = Settings()

def setup_driver():
    """Настройка Selenium драйвера"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Запуск в фоновом режиме
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

def extract_yandex_data(driver, url, expected_data):
    """Извлечение данных со страницы Yandex"""
    print(f"\n{'='*80}")
    print(f"ПРОВЕРКА YANDEX")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Ожидаемые данные из отчета:")
    print(f"  Отзывов: {expected_data.get('reviews_count', 'N/A')}")
    print(f"  Рейтинг: {expected_data.get('rating', 'N/A')}")
    print(f"  С ответами: {expected_data.get('answered', 'N/A')}")
    
    try:
        driver.get(url)
        time.sleep(5)  # Ожидание загрузки
        
        # Прокручиваем страницу для загрузки всех элементов
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        results = {
            'url': url,
            'reviews_count': None,
            'rating': None,
            'answered_count': None,
            'positive': None,
            'negative': None,
            'neutral': None,
            'status': 'success'
        }
        
        # Поиск количества отзывов
        # Пробуем разные селекторы
        review_selectors = [
            '.tabs-select-view__title._name_reviews .tabs-select-view__counter',
            '.business-header-rating-view__text',
            '[class*="review"] [class*="count"]',
            '[class*="отзыв"]'
        ]
        
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        potential_count = int(numbers[0])
                        if 50 < potential_count < 500:
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
        
        # Поиск количества отзывов с ответами для Yandex
        answered_selectors = [
            'span[class*="answered"]',
            '[class*="ответ"]',
            '.tabs-select-view__title._name_reviews'
        ]
        
        for selector in answered_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    # Ищем паттерн "163 с ответами" или "163 ответ"
                    answered_match = re.search(r'(\d+)\s*(?:с\s+ответами|ответами|ответ)', text, re.IGNORECASE)
                    if answered_match:
                        potential_count = int(answered_match.group(1))
                        if 50 < potential_count < 300:
                            results['answered_count'] = potential_count
                            print(f"  ✓ Найдено отзывов с ответами: {potential_count} (селектор: {selector})")
                            break
                if results['answered_count']:
                    break
            except:
                continue
        
        # Если не нашли, ищем в тексте страницы
        if not results['answered_count']:
            try:
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                answered_match = re.search(r'(\d+)\s*(?:с\s+ответами|ответами)', page_text, re.IGNORECASE)
                if answered_match:
                    potential_count = int(answered_match.group(1))
                    if 50 < potential_count < 300:
                        results['answered_count'] = potential_count
                        print(f"  ✓ Найдено отзывов с ответами: {potential_count} (из текста страницы)")
            except:
                pass
        
        # Сравнение с ожидаемыми данными
        print(f"\nСРАВНЕНИЕ С ОТЧЕТОМ:")
        issues = []
        
        if results['reviews_count']:
            if results['reviews_count'] == expected_data.get('reviews_count'):
                print(f"  ✅ Отзывов: {results['reviews_count']} (соответствует отчету)")
            else:
                diff = abs(results['reviews_count'] - expected_data.get('reviews_count', 0))
                print(f"  ⚠️  Отзывов: {results['reviews_count']} (в отчете: {expected_data.get('reviews_count')}, разница: {diff})")
                issues.append(f"Количество отзывов: найдено {results['reviews_count']}, ожидалось {expected_data.get('reviews_count')}")
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
        
        if results['answered_count']:
            if results['answered_count'] == expected_data.get('answered'):
                print(f"  ✅ С ответами: {results['answered_count']} (соответствует отчету)")
            else:
                diff = abs(results['answered_count'] - expected_data.get('answered', 0))
                print(f"  ⚠️  С ответами: {results['answered_count']} (в отчете: {expected_data.get('answered')}, разница: {diff})")
                issues.append(f"Отзывов с ответами: найдено {results['answered_count']}, ожидалось {expected_data.get('answered')}")
        else:
            print(f"  ⚠️  Не удалось извлечь количество отзывов с ответами")
        
        # Проверка детальных данных отзывов
        print(f"\nПРОВЕРКА ДЕТАЛЬНЫХ ДАННЫХ ОТЗЫВОВ:")
        try:
            # Прокручиваем страницу для загрузки всех отзывов
            print("  Прокручиваю страницу для загрузки всех отзывов...")
            for i in range(5):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            
            # Пробуем найти отзывы
            review_elements = driver.find_elements(By.CSS_SELECTOR, '.business-review-view, [class*="review"]')
            print(f"  Найдено элементов отзывов на странице: {len(review_elements)}")
            
            if len(review_elements) > 0:
                # Проверяем первые несколько отзывов
                checked_reviews = min(10, len(review_elements))
                print(f"  Проверяю первые {checked_reviews} отзывов...")
                
                reviews_with_text = 0
                reviews_with_response = 0
                
                for i in range(checked_reviews):
                    try:
                        # Прокручиваем к элементу
                        driver.execute_script("arguments[0].scrollIntoView(true);", review_elements[i])
                        time.sleep(0.5)
                        
                        review = review_elements[i]
                        review_text = review.text.strip()
                        
                        # Проверяем наличие текста
                        if len(review_text) > 50:
                            reviews_with_text += 1
                            print(f"    Отзыв {i+1}: ✓ Текст присутствует ({len(review_text)} символов)")
                        else:
                            print(f"    Отзыв {i+1}: ⚠️  Текст слишком короткий ({len(review_text)} символов)")
                        
                        # Ищем ответ
                        response_elements = review.find_elements(By.CSS_SELECTOR, '[class*="response"], [class*="ответ"], [class*="company"]')
                        if response_elements:
                            reviews_with_response += 1
                            print(f"    Отзыв {i+1}: ✓ Есть ответ организации")
                        else:
                            print(f"    Отзыв {i+1}: - Нет ответа организации")
                    except Exception as e:
                        print(f"    Отзыв {i+1}: ⚠️  Ошибка при проверке: {e}")
                
                print(f"\n  Статистика по проверенным отзывам:")
                print(f"    С текстом: {reviews_with_text}/{checked_reviews}")
                print(f"    С ответами: {reviews_with_response}/{checked_reviews}")
        except Exception as e:
            print(f"  ⚠️  Ошибка при проверке детальных данных: {e}")
        
        results['issues'] = issues
        return results
        
    except Exception as e:
        print(f"  ✗ Ошибка при проверке Yandex: {e}")
        return {'url': url, 'status': 'error', 'error': str(e)}

def extract_2gis_data(driver, url, expected_data):
    """Извлечение данных со страницы 2GIS"""
    print(f"\n{'='*80}")
    print(f"ПРОВЕРКА 2GIS")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Ожидаемые данные из отчета:")
    print(f"  Отзывов: {expected_data.get('reviews_count', 'N/A')}")
    print(f"  Рейтинг: {expected_data.get('rating', 'N/A')}")
    print(f"  С ответами: {expected_data.get('answered', 'N/A')}")
    
    try:
        driver.get(url)
        time.sleep(5)  # Ожидание загрузки
        
        # Прокручиваем страницу для загрузки всех элементов
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        results = {
            'url': url,
            'reviews_count': None,
            'rating': None,
            'answered_count': None,
            'positive': None,
            'negative': None,
            'neutral': None,
            'status': 'success'
        }
        
        # Поиск количества отзывов в 2GIS
        # Используем те же селекторы, что и в парсере
        review_selectors = [
            'span._1xhlznaa',  # Основной селектор для количества отзывов
            '[class*="_1xhlznaa"]',
            'div[class*="review"]',
            '[class*="отзыв"]'
        ]
        
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text.isdigit():
                        potential_count = int(text)
                        if 50 < potential_count < 1000:
                            results['reviews_count'] = potential_count
                            print(f"  ✓ Найдено количество отзывов: {potential_count} (селектор: {selector})")
                            break
                    # Ищем число в тексте
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        potential_count = int(numbers[0])
                        if 50 < potential_count < 1000:
                            results['reviews_count'] = potential_count
                            print(f"  ✓ Найдено количество отзывов: {potential_count} (селектор: {selector})")
                            break
                if results['reviews_count']:
                    break
            except:
                continue
        
        # Если не нашли через селекторы, ищем в тексте страницы
        if not results['reviews_count']:
            try:
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                review_match = re.search(r'(\d+)\s*(?:отзыв|отзывов|отзывa)', page_text, re.IGNORECASE)
                if review_match:
                    potential_count = int(review_match.group(1))
                    if 50 < potential_count < 1000:
                        results['reviews_count'] = potential_count
                        print(f"  ✓ Найдено количество отзывов: {potential_count} (из текста страницы)")
            except:
                pass
        
        # Поиск рейтинга в 2GIS
        rating_selectors = [
            '[class*="rating"]',
            '[class*="star"]',
            '[itemprop="ratingValue"]'
        ]
        
        for selector in rating_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    rating_match = re.search(r'(\d+[.,]\d+)', text)
                    if rating_match:
                        potential_rating = float(rating_match.group(1).replace(',', '.'))
                        if 0 < potential_rating <= 5:
                            results['rating'] = potential_rating
                            print(f"  ✓ Найден рейтинг: {results['rating']} (селектор: {selector})")
                            break
                if results['rating']:
                    break
            except:
                continue
        
        # Поиск количества отзывов с ответами для 2GIS
        # Используем те же селекторы, что и в парсере
        answered_selectors = [
            'span._1iurgbx',  # Основной селектор для "С ответами"
            'span[class*="_1iurgbx"]',
            '[class*="ответ"]'
        ]
        
        for selector in answered_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if 'ответами' in text.lower() or 'ответ' in text.lower():
                        # Ищем число в родительском элементе
                        try:
                            parent = elem.find_element(By.XPATH, './..')
                            parent_text = parent.text.strip()
                            answered_match = re.search(r'(\d+)\s*(?:с\s+ответами|ответами)|(?:с\s+ответами|ответами)\s*(\d+)', parent_text, re.IGNORECASE)
                            if answered_match:
                                potential_count = int(answered_match.group(1) or answered_match.group(2))
                                if 1 < potential_count < 500:
                                    results['answered_count'] = potential_count
                                    print(f"  ✓ Найдено отзывов с ответами: {potential_count} (селектор: {selector})")
                                    break
                        except:
                            pass
                if results['answered_count']:
                    break
            except:
                continue
        
        # Если не нашли, ищем в тексте страницы
        if not results['answered_count']:
            try:
                page_text = driver.find_element(By.TAG_NAME, 'body').text
                answered_match = re.search(r'(\d+)\s*(?:с\s+ответами|ответами)', page_text, re.IGNORECASE)
                if answered_match:
                    potential_count = int(answered_match.group(1))
                    if 1 < potential_count < 500:
                        results['answered_count'] = potential_count
                        print(f"  ✓ Найдено отзывов с ответами: {potential_count} (из текста страницы)")
            except:
                pass
        
        # Сравнение с ожидаемыми данными
        print(f"\nСРАВНЕНИЕ С ОТЧЕТОМ:")
        issues = []
        
        if results['reviews_count']:
            if results['reviews_count'] == expected_data.get('reviews_count'):
                print(f"  ✅ Отзывов: {results['reviews_count']} (соответствует отчету)")
            else:
                diff = abs(results['reviews_count'] - expected_data.get('reviews_count', 0))
                print(f"  ⚠️  Отзывов: {results['reviews_count']} (в отчете: {expected_data.get('reviews_count')}, разница: {diff})")
                issues.append(f"Количество отзывов: найдено {results['reviews_count']}, ожидалось {expected_data.get('reviews_count')}")
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
        
        if results['answered_count']:
            if results['answered_count'] == expected_data.get('answered'):
                print(f"  ✅ С ответами: {results['answered_count']} (соответствует отчету)")
            else:
                diff = abs(results['answered_count'] - expected_data.get('answered', 0))
                print(f"  ⚠️  С ответами: {results['answered_count']} (в отчете: {expected_data.get('answered')}, разница: {diff})")
                issues.append(f"Отзывов с ответами: найдено {results['answered_count']}, ожидалось {expected_data.get('answered')}")
        else:
            print(f"  ⚠️  Не удалось извлечь количество отзывов с ответами")
        
        # Проверка детальных данных отзывов
        print(f"\nПРОВЕРКА ДЕТАЛЬНЫХ ДАННЫХ ОТЗЫВОВ:")
        try:
            # Прокручиваем страницу для загрузки всех отзывов
            print("  Прокручиваю страницу для загрузки всех отзывов...")
            for i in range(10):  # Больше прокруток для 2GIS
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
            
            # Пробуем найти отзывы - используем селекторы из парсера
            review_selectors = [
                '[class*="review"]',
                '[class*="отзыв"]',
                'div[class*="_1"]'  # Общий селектор для элементов отзывов в 2GIS
            ]
            
            review_elements = []
            for selector in review_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) > 10:  # Если нашли достаточно элементов
                        review_elements = elements
                        break
                except:
                    continue
            
            print(f"  Найдено элементов отзывов на странице: {len(review_elements)}")
            
            if len(review_elements) > 0:
                # Проверяем первые несколько отзывов
                checked_reviews = min(10, len(review_elements))
                print(f"  Проверяю первые {checked_reviews} отзывов...")
                
                reviews_with_text = 0
                reviews_with_response = 0
                
                for i in range(checked_reviews):
                    try:
                        # Прокручиваем к элементу
                        driver.execute_script("arguments[0].scrollIntoView(true);", review_elements[i])
                        time.sleep(0.5)
                        
                        review = review_elements[i]
                        review_text = review.text.strip()
                        
                        # Проверяем наличие текста
                        if len(review_text) > 50:
                            reviews_with_text += 1
                            print(f"    Отзыв {i+1}: ✓ Текст присутствует ({len(review_text)} символов)")
                        else:
                            print(f"    Отзыв {i+1}: ⚠️  Текст слишком короткий ({len(review_text)} символов)")
                        
                        # Ищем ответ - используем селектор из парсера
                        response_elements = review.find_elements(By.CSS_SELECTOR, 'div._1wk3bjs, [class*="ответ"], [class*="response"]')
                        if response_elements:
                            reviews_with_response += 1
                            print(f"    Отзыв {i+1}: ✓ Есть ответ организации")
                        else:
                            print(f"    Отзыв {i+1}: - Нет ответа организации")
                    except Exception as e:
                        print(f"    Отзыв {i+1}: ⚠️  Ошибка при проверке: {e}")
                
                print(f"\n  Статистика по проверенным отзывам:")
                print(f"    С текстом: {reviews_with_text}/{checked_reviews}")
                print(f"    С ответами: {reviews_with_response}/{checked_reviews}")
            else:
                print(f"  ⚠️  Не удалось найти элементы отзывов на странице")
        except Exception as e:
            print(f"  ⚠️  Ошибка при проверке детальных данных: {e}")
        
        results['issues'] = issues
        return results
        
    except Exception as e:
        print(f"  ✗ Ошибка при проверке 2GIS: {e}")
        return {'url': url, 'status': 'error', 'error': str(e)}

def main():
    report_file = "output/verification_report_208bc931-92cf-4797-8358-4cd680eeaa9b.json"
    
    if not os.path.exists(report_file):
        print(f"Файл отчета не найден: {report_file}")
        return
    
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    print("="*80)
    print("ПРОВЕРКА ДАННЫХ НА РЕАЛЬНЫХ СТРАНИЦАХ")
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
            
            if card_url == 'N/A':
                print(f"\n⚠️  {source.upper()}: URL карточки отсутствует")
                continue
            
            expected_data = {
                'reviews_count': card.get('card_reviews_count', 0),
                'rating': card.get('card_rating', 'N/A'),
                'answered': card.get('card_answered_reviews_count', 0),
                'positive': card.get('card_reviews_positive', 0),
                'negative': card.get('card_reviews_negative', 0),
                'neutral': card.get('card_reviews_neutral', 0)
            }
            
            if source == 'yandex':
                result = extract_yandex_data(driver, card_url, expected_data)
                all_results.append(('yandex', result))
            elif source == '2gis':
                result = extract_2gis_data(driver, card_url, expected_data)
                all_results.append(('2gis', result))
        
        # Итоговый отчет
        print(f"\n{'='*80}")
        print("ИТОГОВЫЙ ОТЧЕТ")
        print(f"{'='*80}")
        
        all_issues = []
        for source, result in all_results:
            if result.get('status') == 'success':
                issues = result.get('issues', [])
                if issues:
                    all_issues.extend([f"{source.upper()}: {issue}" for issue in issues])
        
        if all_issues:
            print(f"\n⚠️  Найдено несоответствий: {len(all_issues)}")
            for issue in all_issues:
                print(f"  - {issue}")
        else:
            print(f"\n✅ Все данные соответствуют отчету!")
        
        print(f"\n{'='*80}")
        print("РЕКОМЕНДАЦИИ")
        print(f"{'='*80}")
        print("Для полной проверки рекомендуется:")
        print("1. Открыть URL в браузере вручную")
        print("2. Прокрутить страницу до конца для загрузки всех отзывов")
        print("3. Проверить фильтры (все отзывы, не только отфильтрованные)")
        print("4. Открыть несколько отзывов и проверить детальные данные")
        
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

