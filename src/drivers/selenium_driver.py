from __future__ import annotations
import logging
import os
import tempfile
import threading
import sys
from typing import Any, List, Optional, Tuple
from urllib.parse import urlparse

from selenium.webdriver import Chrome, ChromeOptions as SeleniumChromeOptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement

from src.drivers.base_driver import BaseDriver
from src.config.settings import Settings

logger = logging.getLogger(__name__)

def extract_credentials_from_proxy_url(proxy_url: str) -> tuple:
    parsed_url = urlparse(proxy_url)
    if '@' in parsed_url.netloc:
        credentials = parsed_url.netloc.split('@')[0]
        if ':' in credentials:
            username, password = credentials.split(':', 1)
            return username, password
    return None, None

def create_proxy_auth_extension(proxy_host: str, proxy_port: int, username: str, password: str) -> str:
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
            mode: "fixed_servers",
            rules: {
              singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
              },
              bypassList: ["localhost"]
            }
          };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (proxy_host, proxy_port, username, password)

    temp_dir = tempfile.mkdtemp()
    extension_dir = os.path.join(temp_dir, "proxy_auth_extension")
    os.makedirs(extension_dir, exist_ok=True)
    
    manifest_path = os.path.join(extension_dir, "manifest.json")
    background_path = os.path.join(extension_dir, "background.js")
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(manifest_json)
    
    with open(background_path, 'w', encoding='utf-8') as f:
        f.write(background_js)
    
    logger.info(f"Proxy auth extension created at: {extension_dir}")
    return extension_dir

class SeleniumTab:
    def __init__(self, driver: "SeleniumDriver"):
        self._driver = driver
        self._default_timeout = 10

    def set_default_timeout(self, timeout: int):
        self._default_timeout = timeout

    def wait_for_element(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> Optional[WebElement]:
        try:
            wait_timeout = timeout if timeout is not None else self._default_timeout
            if not self._driver or not self._driver.driver:
                return None
            wait = WebDriverWait(self._driver.driver, wait_timeout)
            return wait.until(EC.presence_of_element_located(locator))
        except TimeoutException:
            return None

    def wait_for_response(self, url_pattern: str, timeout: int = 10) -> Optional[str]:
        return self._driver.wait_response(url_pattern, timeout)

class SeleniumDriver(BaseDriver):
    def __init__(self, settings: Settings, proxy: Optional[str] = None):
        self.settings = settings
        self.proxy = proxy
        self.driver: Optional[Chrome] = None
        self._tab: Optional[SeleniumTab] = None
        self._is_running = False
        self.current_url: Optional[str] = None

        self._tab = SeleniumTab(self)

    def _initialize_driver(self):
        if self.driver is not None:
            return

        options = SeleniumChromeOptions()
        
        if self.settings.proxy.enabled and self.settings.proxy.server:
            proxy_url = f"{self.settings.proxy.server}:{self.settings.proxy.port}"
            username = self.settings.proxy.username or ""
            password = self.settings.proxy.password or ""
            
            if self.proxy:
                username, password = extract_credentials_from_proxy_url(self.proxy) or (username, password)
                proxy_url = self.proxy.split('@')[-1] if '@' in self.proxy else proxy_url
            
            if username and password:
                proxy_host = proxy_url.split(':')[0] if ':' in proxy_url else self.settings.proxy.server
                proxy_port = int(proxy_url.split(':')[1]) if ':' in proxy_url else self.settings.proxy.port
                proxy_extension_dir = create_proxy_auth_extension(proxy_host, proxy_port, username, password)
                options.add_argument(f"--load-extension={proxy_extension_dir}")
                logger.info(f"Proxy auth extension loaded from: {proxy_extension_dir}")
            else:
                options.add_argument(f'--proxy-server={proxy_url}')
                logger.info(f"Proxy server configured: {proxy_url}")
        else:
            options.add_argument("--no-proxy-server")
            options.add_argument("--proxy-bypass-list=*")

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        if self.settings.app_config.headless:
            options.add_argument("--headless")

        service = Service(ChromeDriverManager().install())
        self.driver = Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self._is_running = True

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def tab(self) -> SeleniumTab:
        return self._tab

    def navigate(self, url: str) -> None:
        if not self.driver:
            self._initialize_driver()
        self.driver.get(url)
        self.current_url = url

    def get_page_source(self) -> str:
        if not self.driver:
            return ""
        return self.driver.page_source

    def execute_script(self, script: str, *args) -> Any:
        if not self.driver:
            return None
        return self.driver.execute_script(script, *args)

    def wait_response(self, url_pattern: str, timeout: int = 10) -> Optional[str]:
        import re
        start_time = time.time()
        while time.time() - start_time < timeout:
            logs = self.driver.get_log('performance') if self.driver else []
            for log in logs:
                message = log.get('message', '')
                if 'Network.responseReceived' in message and re.search(url_pattern, message):
                    return message
            time.sleep(0.1)
        return None

    def get_response_body(self, response_message: str) -> str:
        return ""

    def close(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None
            self._is_running = False

    def __enter__(self):
        self._initialize_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()