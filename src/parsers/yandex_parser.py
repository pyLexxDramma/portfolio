from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from src.drivers.base_driver import BaseDriver
from src.config.settings import Settings
from src.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)

class YandexParser(BaseParser):
    def __init__(self, driver: BaseDriver, settings: Settings):
        if not isinstance(driver, BaseDriver):
            raise TypeError("YandexParser requires a BaseDriver instance.")

        super().__init__(driver, settings)
        self._url: str = ""

    @staticmethod
    def get_url_pattern() -> str:
        return r'https?://yandex\.ru/maps/\?.*'

    def parse(self, url: str) -> Dict[str, Any]:
        self._url = url
        self._update_progress("Начало парсинга Яндекс.Карт")
        
        try:
            if not self.driver.is_running:
                self.driver.start()
            
            self._update_progress("Переход на страницу поиска...")
            self.driver.navigate(url)
            
            self._update_progress("Поиск карточек...")
            
            result = {
                'source': 'yandex',
                'url': url,
                'cards_data': [],
                'total_cards': 0,
                'aggregated_rating': 0.0,
                'aggregated_reviews_count': 0,
                'aggregated_positive_reviews': 0,
                'aggregated_negative_reviews': 0,
                'aggregated_answered_reviews_count': 0,
                'aggregated_avg_response_time': None
            }
            
            self._update_progress("Парсинг завершен (минимальная версия)")
            return result
            
        except Exception as e:
            logger.error(f"Error in YandexParser.parse: {e}", exc_info=True)
            self._update_progress(f"Ошибка: {str(e)}")
            raise

