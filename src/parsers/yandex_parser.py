from __future__ import annotations
import json
import os
import re
import logging
import time
import urllib.parse
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field
from selenium.webdriver.remote.webelement import WebElement as SeleniumWebElement

from src.drivers.base_driver import BaseDriver, DOMNode
from src.config.settings import Settings
from src.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class YandexParser(BaseParser):
    def __init__(self, driver: BaseDriver, settings: Settings):
        if not isinstance(driver, BaseDriver):
            raise TypeError("YandexParser requires a BaseDriver instance.")

        super().__init__(driver, settings)
        self._url: str = ""

        self._captcha_wait_time: int = getattr(self._settings.parser, 'yandex_captcha_wait', 20)
        self._reviews_scroll_step: int = getattr(self._settings.parser, 'yandex_reviews_scroll_step', 500)
        self._reviews_scroll_iterations_max: int = getattr(self._settings.parser, 'yandex_reviews_scroll_max_iter', 100)
        self._reviews_scroll_iterations_min: int = getattr(self._settings.parser, 'yandex_reviews_scroll_min_iter', 30)
        self._max_records: int = getattr(self._settings.parser, 'max_records', 1000)

        self._card_selectors: List[str] = getattr(self._settings.parser, 'yandex_card_selectors', [
            "div.search-business-snippet-view",
            "div.search-snippet-view__body._type_business",
            "a[href*='/maps/org/']:not([href*='/gallery/'])"
        ])
        self._scroll_container: str = getattr(self._settings.parser, 'yandex_scroll_container', 
                                               ".scroll__container, .scroll__content, .search-list-view__list")
        self._scrollable_element_selector: str = getattr(self._settings.parser, 'yandex_scrollable_element_selector',
                                                         ".scroll__container, .scroll__content, [class*='search-list-view'], [class*='scroll']")
        self._scroll_step: int = getattr(self._settings.parser, 'yandex_scroll_step', 400)
        self._scroll_max_iter: int = getattr(self._settings.parser, 'yandex_scroll_max_iter', 200)
        self._scroll_wait_time: float = getattr(self._settings.parser, 'yandex_scroll_wait_time', 1.5)
        self._min_cards_threshold: int = getattr(self._settings.parser, 'yandex_min_cards_threshold', 500)

        self._data_mapping: Dict[str, str] = {
            'search_query_name': 'Название поиска',
            'total_cards_found': 'Всего карточек найдено',
            'aggregated_rating': 'Общий рейтинг',
            'aggregated_reviews_count': 'Всего отзывов',
            'aggregated_positive_reviews': 'Всего положительных отзывов',
            'aggregated_negative_reviews': 'Всего отрицательных отзывов',
            'aggregated_avg_response_time': 'Среднее время ответа (дни)',

            'card_name': 'Название карточки',
            'card_address': 'Адрес карточки',
            'card_rating': 'Рейтинг карточки',
            'card_reviews_count': 'Отзывов по карточке',
            'card_website': 'Сайт карточки',
            'card_phone': 'Телефон карточки',
            'card_rubrics': 'Рубрики карточки',
            'card_response_status': 'Статус ответа (карточка)',
            'card_avg_response_time': 'Среднее время ответа (дни, карточка)',
            'card_reviews_positive': 'Положительных отзывов (карточка)',
            'card_reviews_negative': 'Отрицательных отзывов (карточка)',
            'card_reviews_texts': 'Тексты отзывов (карточка)',
            'review_rating': 'Оценка отзыва',
            'review_text': 'Текст отзыва',
        }

        self._current_page_number: int = 1
        self._aggregated_data: Dict[str, Any] = {
            'total_cards': 0,
            'total_rating_sum': 0.0,
            'total_reviews_count': 0,
            'total_positive_reviews': 0,
            'total_negative_reviews': 0,
            'total_answered_count': 0,
            'total_answered_reviews_count': 0,
            'total_unanswered_reviews_count': 0,
            'total_response_time_sum_days': 0.0,
            'total_response_time_calculated_count': 0,
        }
        self._collected_card_data: List[Dict[str, Any]] = []
        self._search_query_name: str = ""

    @staticmethod
    def get_url_pattern() -> str:
        return r'https?://yandex\.ru/maps/\?.*'

    def _get_page_source_and_soup(self) -> Tuple[str, BeautifulSoup]:
        page_source = self.driver.get_page_source()
        soup = BeautifulSoup(page_source, "lxml")
        return page_source, soup

    def check_captcha(self) -> None:
        page_source, soup = self._get_page_source_and_soup()

        is_captcha = soup.find("div", {"class": "CheckboxCaptcha"}) or \
                     soup.find("div", {"class": "AdvancedCaptcha"})

        if is_captcha:
            logger.warning(f"Captcha detected. Waiting for {self._captcha_wait_time} seconds.")
            time.sleep(self._captcha_wait_time)
            self.check_captcha()

    def _get_card_snippet_data(self, card_element: Tag) -> Optional[Dict[str, Any]]:
        try:
            name_selectors = [
                'h1.card-title-view__title',
                '.search-business-snippet-view__title',
                'a.search-business-snippet-view__title',
                'a.catalogue-snippet-view__title',
                'a[class*="title"]',
                'h2[class*="title"]',
                'h3[class*="title"]',
            ]
            name = ''
            for selector in name_selectors:
                name_element = card_element.select_one(selector)
                if name_element:
                    name = name_element.get_text(strip=True)
                    if name:
                        break

            address_selectors = [
                'div.business-contacts-view__address-link',
                '.search-business-snippet-view__address',
                'div[class*="address"]',
                'span[class*="address"]',
            ]
            address = ''
            for selector in address_selectors:
                address_element = card_element.select_one(selector)
                if address_element:
                    address = address_element.get_text(strip=True)
                    if address:
                        break

            rating_selectors = [
                'span.business-rating-badge-view__rating-text',
                '.search-business-snippet-view__rating-text',
                'span[class*="rating"]',
                'div[class*="rating"]',
            ]
            rating = ''
            for selector in rating_selectors:
                rating_element = card_element.select_one(selector)
                if rating_element:
                    rating = rating_element.get_text(strip=True)
                    if rating:
                        break

            reviews_selectors = [
                'a.business-review-view__rating',
                '.search-business-snippet-view__link-reviews',
                'a[class*="review"]',
                'span[class*="review"]',
            ]
            reviews_count = 0
            for selector in reviews_selectors:
                reviews_element = card_element.select_one(selector)
                if reviews_element:
                    reviews_count_text = reviews_element.get_text(strip=True)
                    if reviews_count_text:
                        match = re.search(r'(\d+)', reviews_count_text)
                        if match:
                            reviews_count = int(match.group(0))
                            break
                if reviews_count > 0:
                    break

            website_selectors = [
                'a[itemprop="url"]',
                'a[class*="website"]',
                'a[href^="http"]',
            ]
            website = ''
            for selector in website_selectors:
                website_element = card_element.select_one(selector)
                if website_element:
                    website = website_element.get('href', '')
                    if website and 'yandex.ru' not in website:
                        break

            phone_selectors = [
                'span.business-contacts-view__phone-number',
                'a[href^="tel:"]',
                'span[class*="phone"]',
            ]
            phone = ''
            for selector in phone_selectors:
                phone_element = card_element.select_one(selector)
                if phone_element:
                    phone = phone_element.get_text(strip=True)
                    if not phone and phone_element.get('href'):
                        phone = phone_element.get('href').replace('tel:', '').strip()
                    if phone:
                        phone = phone.replace('Показать телефон', '').replace('показать телефон', '').strip()
                        break

            rubrics_elements = card_element.select('a.rubric-view__title, a[class*="rubric"], a[href*="/rubric/"]')
            rubrics = "; ".join([r.get_text(strip=True) for r in rubrics_elements]) if rubrics_elements else ''

            return {
                'card_name': name,
                'card_address': address,
                'card_rating': rating,
                'card_reviews_count': reviews_count,
                'card_website': website,
                'card_phone': phone,
                'card_rubrics': rubrics,
                'card_response_status': "UNKNOWN",
                'card_avg_response_time': "",
                'card_reviews_positive': 0,
                'card_reviews_negative': 0,
                'card_reviews_texts': "",
                'card_answered_reviews_count': 0,
                'card_unanswered_reviews_count': reviews_count,
                'detailed_reviews': [],
                'review_rating': None,
                'review_text': None,
            }
        except Exception as e:
            logger.error(f"Error processing Yandex card snippet: {e}")
            return None

    def _extract_card_data_from_detail_page(self, card_details_soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        try:
            card_snippet = {
                'card_name': '',
                'card_address': '',
                'card_rating': '',
                'card_reviews_count': 0,
                'card_website': '',
                'card_phone': '',
                'card_rubrics': '',
                'card_response_status': "UNKNOWN",
                'card_avg_response_time': "",
                'card_reviews_positive': 0,
                'card_reviews_negative': 0,
                'card_reviews_texts': "",
                'card_answered_reviews_count': 0,
                'card_unanswered_reviews_count': 0,
                'detailed_reviews': [],
            }
            

            name_selectors = [
                'h1.card-title-view__title',
                'h1[class*="title"]',
                'h1[class*="card-title"]',
                'h1.business-card-title-view__title',
                'h1',
                'div[class*="title"]',
                'span[class*="title"]',
            ]
            
            name_detail = None
            for selector in name_selectors:
                name_detail = card_details_soup.select_one(selector)
                if name_detail:
                    name_text = name_detail.get_text(strip=True)
                    if name_text:
                        card_snippet['card_name'] = name_text
                        logger.debug(f"Found card name using selector '{selector}': {name_text[:50]}")
                        break
            
            if not card_snippet.get('card_name'):
                logger.warning(f"Could not find card name on detail page. Available h1 tags: {[h.get_text(strip=True)[:50] for h in card_details_soup.select('h1')]}")


            address_selectors = [
                'div.business-contacts-view__address-link',
                'div[class*="address"]',
                'span[class*="address"]',
                'div[class*="location"]',
                'span[class*="location"]',
                '[itemprop="address"]',
                'div[data-test="address"]',
            ]
            
            address_detail = None
            for selector in address_selectors:
                address_detail = card_details_soup.select_one(selector)
                if address_detail:
                    address_text = address_detail.get_text(strip=True)
                    if address_text and len(address_text) > 5:
                        card_snippet['card_address'] = address_text
                        logger.debug(f"Found card address using selector '{selector}': {address_text[:50]}")
                        break
            

            if card_snippet.get('card_address'):
                card_snippet['card_address'] = self._normalize_address(card_snippet['card_address'])
            
            if not card_snippet.get('card_address') or len(card_snippet.get('card_address', '').strip()) < 5:
                logger.warning(f"Card address not found for card: {card_snippet.get('card_name', 'Unknown')[:50]}")
                card_snippet['card_address'] = ''

            rating_detail = card_details_soup.select_one('span.business-rating-badge-view__rating-text')
            card_snippet['card_rating'] = rating_detail.get_text(strip=True) if rating_detail else ''

            website_detail = card_details_soup.select_one('a[itemprop="url"], .business-website-view__link')
            card_snippet['card_website'] = website_detail.get('href') if website_detail else ''


            phone_selectors = [
                'span.business-contacts-view__phone-number',
                'a[href^="tel:"]',
                'span[class*="phone"]',
                'div[class*="phone"]',
                'span[itemprop="telephone"]',
                'a.business-contacts-view__phone-link',
            ]
            
            phone_text = ""
            for selector in phone_selectors:
                phone_elements = card_details_soup.select(selector)
                if phone_elements:
                    for phone_elem in phone_elements:
                        phone_text = phone_elem.get_text(strip=True)
                        if not phone_text and phone_elem.get('href'):
                            href = phone_elem.get('href', '')
                            if href.startswith('tel:'):
                                phone_text = href.replace('tel:', '').strip()
                        if phone_text:
                            phone_text = phone_text.replace('Показать телефон', '').replace('показать телефон', '').strip()
                            break
                if phone_text:
                    break
            
            card_snippet['card_phone'] = phone_text


            rubric_selectors = [
                'a.rubric-view__title',
                'a[class*="rubric"]',
                'span[class*="rubric"]',
                'div[class*="rubric"]',
                'a[href*="/rubric/"]',
            ]
            
            rubrics_list = []
            for selector in rubric_selectors:
                rubrics_detail = card_details_soup.select(selector)
                if rubrics_detail:
                    for r in rubrics_detail:
                        rubric_text = r.get_text(strip=True)
                        if rubric_text and rubric_text not in rubrics_list:
                            rubrics_list.append(rubric_text)
                    if rubrics_list:
                        break
            
            card_snippet['card_rubrics'] = "; ".join(rubrics_list) if rubrics_list else ""


            response_selectors = [
                '.business-header-view__quick-response-badge',
                'div[class*="response"]',
                'span[class*="response"]',
                'div.business-response-view',
            ]
            
            response_status = "UNKNOWN"
            for selector in response_selectors:
                response_status_element = card_details_soup.select_one(selector)
                if response_status_element:
                    response_text = response_status_element.get_text(strip=True)
                    if response_text:
                        response_status = response_text
                        break
            
            card_snippet['card_response_status'] = response_status
            
            time_selectors = [
                '.business-header-view__avg-response-time',
                'div[class*="response-time"]',
                'span[class*="response-time"]',
            ]
            
            avg_response_time_text = ""
            for selector in time_selectors:
                avg_response_time_element = card_details_soup.select_one(selector)
                if avg_response_time_element:
                    avg_response_time_text = avg_response_time_element.get_text(strip=True)
                    if avg_response_time_text:
                        break
            
            if avg_response_time_text:
                if "час" in avg_response_time_text.lower() or "hour" in avg_response_time_text.lower():
                    match = re.search(r'(\d+(\.\d+)?)\s*(час|hour)', avg_response_time_text, re.IGNORECASE)
                    if match:
                        hours = float(match.group(1))
                        card_snippet['card_avg_response_time'] = round(hours / 24, 2)
                elif "день" in avg_response_time_text.lower() or "day" in avg_response_time_text.lower():
                    match = re.search(r'(\d+(\.\d+)?)\s*(день|day)', avg_response_time_text, re.IGNORECASE)
                    if match:
                        card_snippet['card_avg_response_time'] = float(match.group(1))
                elif "недел" in avg_response_time_text.lower() or "week" in avg_response_time_text.lower():
                    match = re.search(r'(\d+(\.\d+)?)\s*(недел|week)', avg_response_time_text, re.IGNORECASE)
                    if match:
                        weeks = float(match.group(1))
                        card_snippet['card_avg_response_time'] = weeks * 7
                elif "месяц" in avg_response_time_text.lower() or "month" in avg_response_time_text.lower():
                    match = re.search(r'(\d+(\.\d+)?)\s*(месяц|month)', avg_response_time_text, re.IGNORECASE)
                    if match:
                        months = float(match.group(1))
                        card_snippet['card_avg_response_time'] = months * 30
                else:
                    card_snippet['card_avg_response_time'] = ""
            else:
                card_snippet['card_avg_response_time'] = ""

            reviews_data = self._get_card_reviews_info()
            card_snippet['card_reviews_count'] = reviews_data.get('reviews_count', 0)
            card_snippet['card_reviews_positive'] = reviews_data.get('positive_reviews', 0)
            card_snippet['card_reviews_negative'] = reviews_data.get('negative_reviews', 0)

            review_texts = []
            for detail in reviews_data.get('details', []):
                if detail.get('review_text'):
                    review_texts.append(detail.get('review_text'))
            card_snippet['card_reviews_texts'] = "; ".join(review_texts)
            card_snippet['detailed_reviews'] = reviews_data.get('details', [])

            answered_reviews_count = 0
            try:
                answered_selectors = [
                    'div[class*="answered"]',
                    'span[class*="answered"]',
                    'div.business-review-view__response',
                    'div.review-item-view__response',
                ]
                for selector in answered_selectors:
                    answered_elements = card_details_soup.select(selector)
                    if answered_elements:
                        answered_reviews_count = len(answered_elements)
                        break
            except Exception as e:
                logger.warning(f"Error counting answered reviews: {e}")
            
            card_snippet['card_answered_reviews_count'] = answered_reviews_count
            card_snippet['card_unanswered_reviews_count'] = max(0, card_snippet['card_reviews_count'] - answered_reviews_count)

            if not card_snippet.get('card_name'):
                logger.warning(f"Card name is empty. Card snippet keys: {list(card_snippet.keys())}")
                try:
                    debug_html_path = os.path.join('output', f'debug_card_no_name_{int(time.time())}.html')
                    os.makedirs('output', exist_ok=True)
                    with open(debug_html_path, 'w', encoding='utf-8') as f:
                        f.write(str(card_details_soup))
                    logger.info(f"Saved debug HTML to {debug_html_path}")
                except Exception as e:
                    logger.error(f"Could not save debug HTML: {e}")
                return None

            card_snippet['source'] = 'yandex'
            
            logger.debug(f"Successfully extracted card data: name='{card_snippet.get('card_name', '')[:50]}', address='{card_snippet.get('card_address', '')[:50]}'")
            return card_snippet
        except Exception as e:
            logger.error(f"Error extracting card data from detail page: {e}", exc_info=True)
            return None

    def _update_aggregated_data(self, card_snippet: Dict[str, Any]) -> None:
        try:
            rating_str = str(card_snippet.get('card_rating', '')).replace(',', '.').strip()
            try:
                card_rating_float = float(rating_str) if rating_str and rating_str.replace('.', '', 1).isdigit() else 0.0
            except (ValueError, TypeError):
                card_rating_float = 0.0

            self._aggregated_data['total_rating_sum'] += card_rating_float

            reviews_count = card_snippet.get('card_reviews_count', 0) or 0
            positive_reviews = card_snippet.get('card_reviews_positive', 0) or 0
            negative_reviews = card_snippet.get('card_reviews_negative', 0) or 0
            answered_reviews = card_snippet.get('card_answered_reviews_count', 0) or 0

            self._aggregated_data['total_reviews_count'] += reviews_count
            self._aggregated_data['total_positive_reviews'] += positive_reviews
            self._aggregated_data['total_negative_reviews'] += negative_reviews
            self._aggregated_data['total_answered_reviews_count'] += answered_reviews
            self._aggregated_data['total_unanswered_reviews_count'] += max(0, reviews_count - answered_reviews)

            if card_snippet.get('card_response_status') != 'UNKNOWN' or answered_reviews > 0:
                self._aggregated_data['total_answered_count'] += 1

            if card_snippet.get('card_avg_response_time'):
                try:
                    response_time_str = str(card_snippet['card_avg_response_time']).strip()
                    if response_time_str:
                        response_time_days = float(response_time_str)
                        if response_time_days > 0:
                            self._aggregated_data['total_response_time_sum_days'] += response_time_days
                            self._aggregated_data['total_response_time_calculated_count'] += 1
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not convert response time to float for card '{card_snippet.get('card_name', 'Unknown')}': {card_snippet.get('card_avg_response_time')}")

            logger.info(f"Aggregated data updated for '{card_snippet.get('card_name', 'Unknown')}': "
                       f"rating={card_rating_float}, reviews={reviews_count}, "
                       f"positive={positive_reviews}, negative={negative_reviews}")
        except Exception as e:
            logger.warning(
                f"Could not parse rating or other data for aggregation for card '{card_snippet.get('card_name', 'Unknown')}': {e}", exc_info=True)

    def _get_card_reviews_info(self) -> Dict[str, Any]:
        reviews_info = {'reviews_count': 0, 'positive_reviews': 0, 'negative_reviews': 0, 'texts': [], 'details': []}

        try:
            page_source, soup_content = self._get_page_source_and_soup()
        except Exception as e:
            logger.error(f"Failed to get page source before handling reviews: {e}")
            return reviews_info

        reviews_count_total = 0
        try:
            reviews_link = soup_content.select_one('a[href*="/reviews/"]')
            if reviews_link:
                reviews_url = reviews_link.get('href')
                if reviews_url:
                    if not reviews_url.startswith('http'):
                        reviews_url = urllib.parse.urljoin("https://yandex.ru", reviews_url)
                    logger.info(f"Navigating to reviews page: {reviews_url}")
                    try:
                        self.driver.navigate(reviews_url)
                        time.sleep(3)
                        page_source, soup_content = self._get_page_source_and_soup()
                    except Exception as nav_error:
                        logger.warning(f"Could not navigate to reviews page: {nav_error}")
        except Exception as e:
            logger.warning(f"Error trying to navigate to reviews: {e}")

        try:
            count_selectors = [
                'div.tabs-select-view__counter',
                '.search-business-snippet-view__link-reviews',
                'a[href*="/reviews/"]',
                'span.business-rating-badge-view__reviews-count',
                'div.business-header-view__reviews-count',
                'a.business-review-view__rating',
            ]

            for selector in count_selectors:
                count_elements = soup_content.select(selector)
            if count_elements:
                    for elem in count_elements:
                        reviews_count_text = elem.get_text(strip=True)
                        matches = re.findall(r'(\d+)', reviews_count_text)
                        if matches:
                            potential_count = max([int(m) for m in matches])
                            if potential_count > reviews_count_total:
                                reviews_count_total = potential_count
                                logger.info(f"Found reviews count {reviews_count_total} using selector: {selector}")

            if reviews_count_total > 0:
                logger.info(f"Total reviews found on page: {reviews_count_total}")
            else:
                logger.warning("Could not find reviews count element. Trying to navigate to reviews tab...")
                try:
                    reviews_tab = soup_content.select_one('a[href*="/reviews/"], button[data-tab="reviews"]')
                    if reviews_tab:
                        reviews_url = reviews_tab.get('href')
                        if reviews_url:
                            if not reviews_url.startswith('http'):
                                reviews_url = urllib.parse.urljoin("https://yandex.ru", reviews_url)
                            logger.info(f"Navigating to reviews page: {reviews_url}")
                            self.driver.navigate(reviews_url)
                            time.sleep(3)
                            page_source, soup_content = self._get_page_source_and_soup()
                            for selector in count_selectors:
                                count_elements = soup_content.select(selector)
                                if count_elements:
                                    for elem in count_elements:
                                        reviews_count_text = elem.get_text(strip=True)
                                        matches = re.findall(r'(\d+)', reviews_count_text)
                                        if matches:
                                            potential_count = max([int(m) for m in matches])
                                            if potential_count > reviews_count_total:
                                                reviews_count_total = potential_count
                except Exception as nav_error:
                    logger.warning(f"Could not navigate to reviews tab: {nav_error}")
        except (ValueError, AttributeError, IndexError) as e:
            logger.warning(f"Could not determine review count: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting review count: {e}")
            return reviews_info

        if reviews_count_total == 0:
            logger.warning("No reviews found or reviews count is 0")
            return reviews_info

        scroll_iterations = 0
        max_scroll_iterations = self._reviews_scroll_iterations_max
        min_scroll_iterations = self._reviews_scroll_iterations_min
        scroll_step = self._reviews_scroll_step

        scroll_container_script = """
        var containers = document.querySelectorAll('.scroll__container, [class*="scroll"], [class*="reviews"]');
        for (var i = 0; i < containers.length; i++) {
            var container = containers[i];
            if (container.scrollHeight > container.clientHeight && container.scrollHeight > 500) {
                return container;
            }
        }
        return null;
        """