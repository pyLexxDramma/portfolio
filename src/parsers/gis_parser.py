from __future__ import annotations
import json
import re
import logging
import time
import urllib.parse
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from src.drivers.base_driver import BaseDriver
from src.config.settings import Settings
from src.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class GisParser(BaseParser):
    def __init__(self, driver: BaseDriver, settings: Settings):
        super().__init__(driver, settings)
        self._url: str = ""

        self._scroll_step: int = getattr(self._settings.parser, 'gis_scroll_step', 500)
        self._scroll_max_iter: int = getattr(self._settings.parser, 'gis_scroll_max_iter', 100)
        self._scroll_wait_time: float = getattr(self._settings.parser, 'gis_scroll_wait_time', 0.5)
        self._reviews_scroll_step: int = getattr(self._settings.parser, 'gis_reviews_scroll_step', 500)
        self._reviews_scroll_iterations_max: int = getattr(self._settings.parser, 'gis_reviews_scroll_max_iter', 100)
        self._reviews_scroll_iterations_min: int = getattr(self._settings.parser, 'gis_reviews_scroll_min_iter', 30)
        self._max_records: int = getattr(self._settings.parser, 'max_records', 1000)

        self._card_selectors: List[str] = getattr(self._settings.parser, 'gis_card_selectors', [
            'a[href*="/firm/"]',              'a[href*="/station/"]',          ])

        self._scrollable_element_selector: str = getattr(self._settings.parser, 'gis_scroll_container', 
                                                       '[class*="_1rkbbi0x"], [class*="scroll"], [class*="list"], [class*="results"]')

    def _add_xhr_counter_script(self) -> str:
        xhr_script = r'''
            (function() {
                var oldOpen = XMLHttpRequest.prototype.open;
                XMLHttpRequest.prototype.open = function(method, url, async, user, pass) {
                    if (url.match(/^https?\:\/\/[^\/]*2gis\.[a-z]+/i)) {
                        if (window.openHTTPs === undefined) {
                            window.openHTTPs = 1;
                        } else {
                            window.openHTTPs++;
                        }
                    }
                    oldOpen.call(this, method, url, async, user, pass);
                }
            })();
        '''