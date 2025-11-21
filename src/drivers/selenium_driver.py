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
                logger.error("WebDriver not initialized for wait_for_element.")
                return None
            return WebDriverWait(self._driver.driver, wait_timeout).until(
                EC.presence_of_element_located(locator)
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for element {locator}.")
            return None
        except WebDriverException as e:
            logger.error(f"WebDriverException in wait_for_element with {locator}: {e}", exc_info=True)
            return None

    def wait_for_elements(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> List[WebElement]:
        try:
            wait_timeout = timeout if timeout is not None else self._default_timeout
            if not self._driver or not self._driver.driver:
                logger.error("WebDriver not initialized for wait_for_elements.")
                return []
            WebDriverWait(self._driver.driver, wait_timeout).until(
                EC.presence_of_all_elements_located(locator)
            )
            return self._driver.driver.find_elements(*locator)
        except TimeoutException:
            logger.warning(f"Timeout waiting for elements {locator}.")
            return []
        except WebDriverException as e:
            logger.error(f"WebDriverException in wait_for_elements with {locator}: {e}", exc_info=True)
            return []

class SeleniumDriver(BaseDriver):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.driver: Optional[Chrome] = None
        self._tab: Optional[SeleniumTab] = None
        self._is_running = False
        self.current_url: Optional[str] = None
        self._tab = SeleniumTab(self)

    def _get_proxy_url(self) -> Optional[str]:
        if not self.settings.proxy.enabled:
            return None
        if self.settings.proxy.username and self.settings.proxy.password:
            return f"{self.settings.proxy.type}://{self.settings.proxy.username}:{self.settings.proxy.password}@{self.settings.proxy.server}:{self.settings.proxy.port}"
        else:
            return f"{self.settings.proxy.type}://{self.settings.proxy.server}:{self.settings.proxy.port}"

    def _initialize_driver(self):
        options = SeleniumChromeOptions()
        
        if self.settings.chrome.headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            logger.info("Chrome running in headless mode.")
        else:
            logger.info("Chrome running in visible mode.")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        if self.settings.chrome.silent_browser:
            options.add_argument("--log-level=3")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        if self.settings.chrome.start_maximized and not self.settings.chrome.headless:
            options.add_argument("--start-maximized")

        proxy_url = self._get_proxy_url()
        if proxy_url:
            parsed_proxy = urlparse(proxy_url)
            username, password = extract_credentials_from_proxy_url(proxy_url)
            
            if username and password:
                logger.info(f"Using proxy with authentication: {parsed_proxy.hostname}:{parsed_proxy.port}")
                try:
                    proxy_host = parsed_proxy.hostname
                    proxy_port = parsed_proxy.port or (8080 if parsed_proxy.scheme == 'http' else 443)
                    extension_dir = create_proxy_auth_extension(proxy_host, proxy_port, username, password)
                    options.add_argument(f"--load-extension={extension_dir}")
                    logger.info(f"Proxy auth extension loaded from: {extension_dir}")
                except Exception as e:
                    logger.error(f"Failed to create proxy auth extension: {e}. Trying without auth...")
                    proxy_host = parsed_proxy.hostname
                    proxy_port = parsed_proxy.port or (8080 if parsed_proxy.scheme == 'http' else 443)
                    options.add_argument(f"--proxy-server={parsed_proxy.scheme}://{proxy_host}:{proxy_port}")
            else:
                logger.info(f"Using proxy without authentication: {proxy_url}")
                options.add_argument(f"--proxy-server={proxy_url}")
        else:
            options.add_argument("--no-proxy-server")
            options.add_argument("--proxy-bypass-list=*")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        try:
            logger.info("Using ChromeDriverManager to automatically download compatible ChromeDriver...")
            sys.stdout.flush()
            chromedriver_path = ChromeDriverManager().install()
            logger.info(f"ChromeDriverManager downloaded/verified ChromeDriver at: {chromedriver_path}")
            service = Service(chromedriver_path)
            
            logger.info("Creating Chrome WebDriver instance...")
            sys.stdout.flush()
            
            driver_created = threading.Event()
            driver_result = [None]
            error_result = [None]
            
            def create_driver_thread():
                try:
                    logger.info("Thread: Starting Chrome() call...")
                    sys.stdout.flush()
                    driver_result[0] = Chrome(service=service, options=options)
                    logger.info("Thread: Chrome() call completed.")
                    sys.stdout.flush()
                except Exception as e:
                    error_result[0] = e
                    logger.error(f"Thread: Error in Chrome() call: {e}", exc_info=True)
                finally:
                    driver_created.set()
            
            thread = threading.Thread(target=create_driver_thread, daemon=True)
            thread.start()
            
            if driver_created.wait(timeout=60):
                if error_result[0]:
                    raise error_result[0]
                self.driver = driver_result[0]
                if not self.driver:
                    raise Exception("Chrome WebDriver instance is None after creation")
                logger.info("Chrome() call completed successfully.")
            else:
                raise TimeoutException("Chrome WebDriver creation timed out after 60 seconds.")
            
            logger.info("Chrome WebDriver instance created successfully.")
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(5)
            
            if self.settings.chrome.start_maximized and not self.settings.chrome.headless:
                try:
                    self.driver.maximize_window()
                    logger.info("Chrome window maximized.")
                except Exception as e:
                    logger.warning(f"Could not maximize window: {e}")
            
        except WebDriverException as e:
            logger.error(f"WebDriverException during initialization: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"General error during WebDriver initialization: {e}", exc_info=True)
            raise

    def start(self) -> None:
        if not self._is_running:
            try:
                logger.info("=" * 60)
                logger.info("Starting SeleniumDriver initialization...")
                logger.info(f"Headless mode: {self.settings.chrome.headless}")
                logger.info("=" * 60)
                self._initialize_driver()
                self._is_running = True
                logger.info("SeleniumDriver started successfully.")
            except Exception as e:
                logger.error(f"Error starting SeleniumDriver: {e}", exc_info=True)
                raise
        else:
            logger.warning("SeleniumDriver is already running.")

    def stop(self) -> None:
        if self._is_running and self.driver:
            try:
                self.driver.quit()
                self._is_running = False
                self.driver = None
                self.current_url = None
                logger.info("SeleniumDriver stopped.")
            except WebDriverException as e:
                logger.error(f"WebDriverException during stop: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error stopping SeleniumDriver: {e}", exc_info=True)
        elif not self._is_running:
            logger.warning("SeleniumDriver is not running.")

    def navigate(self, url: str) -> None:
        if not self._is_running or not self.driver:
            raise RuntimeError(f"{self.__class__.__name__} is not running or driver not initialized.")
        
        try:
            self.driver.get(url)
            self.current_url = self.driver.current_url
            logger.info(f"Navigated to: {url}")
        except WebDriverException as e:
            error_msg = str(e).lower()
            if 'proxy' in error_msg or 'err_no_supported_proxies' in error_msg or 'net::err_proxy' in error_msg:
                logger.error(f"Proxy error while navigating to {url}: {e}")
                if self._get_proxy_url():
                    logger.warning(f"Current proxy: {self._get_proxy_url()}")
            else:
                logger.error(f"WebDriverException navigating to {url}: {e}", exc_info=True)
            if self.driver: 
                try:
                    self.current_url = self.driver.current_url
                except:
                    pass
            raise

    def get_page_source(self) -> str:
        if not self._is_running or not self.driver:
            raise RuntimeError(f"{self.__class__.__name__} is not running or driver not initialized.")
        try:
            return self.driver.page_source
        except WebDriverException as e:
            logger.error(f"WebDriverException getting page source: {e}", exc_info=True)
            return ""

    def execute_script(self, script: str, *args) -> Any:
        if not self._is_running or not self.driver:
            raise RuntimeError(f"{self.__class__.__name__} is not running or driver not initialized.")
        try:
            return self.driver.execute_script(script, *args)
        except WebDriverException as e:
            logger.error(f"WebDriverException executing script: {e}", exc_info=True)
            raise

    def get_elements_by_locator(self, locator: Tuple[str, str]) -> List[WebElement]:
        if not self._is_running or not self.driver:
            raise RuntimeError(f"{self.__class__.__name__} is not running or driver not initialized.")
        try:
            return self.driver.find_elements(*locator)
        except WebDriverException as e:
            logger.error(f"WebDriverException getting elements: {e}", exc_info=True)
            return []

    def wait_response(self, url_pattern: str, timeout: int = 10) -> Optional[Any]:
        logger.warning("wait_response is not fully implemented for SeleniumDriver")
        return None

    def get_response_body(self, response: Any) -> Optional[str]:
        logger.warning("get_response_body is not fully implemented for SeleniumDriver")
        return None

    def set_default_timeout(self, timeout: int):
        self._tab.set_default_timeout(timeout)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def tab(self):
        return self._tab

