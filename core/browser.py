"""
浏览器管理模块
负责初始化和管理 Selenium WebDriver
"""

import time
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BrowserManager:
    """浏览器管理器，支持 Chrome 和 Edge"""

    def __init__(self, headless=False, user_data_dir=None, browser_type="chrome"):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.browser_type = browser_type.lower()
        self.driver = None

    def get_driver(self):
        if self.driver is None:
            self._create_driver()
        return self.driver

    def _create_driver(self):
        if self.browser_type == "edge":
            self._create_edge_driver()
        else:
            self._create_chrome_driver()

    def _apply_common_options(self, options):
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--window-size=1920,1080")
        if self.user_data_dir:
            options.add_argument(f"--user-data-dir={self.user_data_dir}")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--lang=zh-CN")

    def _create_chrome_driver(self):
        options = ChromeOptions()
        self._apply_common_options(options)
        try:
            self.driver = webdriver.Chrome(options=options)
        except Exception:
            print("正在尝试自动安装 ChromeDriver...")
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except ImportError:
                print("请安装 webdriver_manager: pip install webdriver-manager")
                raise
        self._apply_anti_detection()

    def _create_edge_driver(self):
        options = EdgeOptions()
        self._apply_common_options(options)
        if not self.user_data_dir:
            if os.name == "nt":
                edge_data = os.path.join(
                    os.environ.get("LOCALAPPDATA", ""),
                    "Microsoft", "Edge", "User Data"
                )
            elif os.name == "posix":
                edge_data = os.path.expanduser(
                    "~/.config/microsoft-edge" if not sys.platform == "darwin"
                    else "~/Library/Application Support/Microsoft Edge"
                )
            else:
                edge_data = None
            if edge_data and os.path.isdir(edge_data):
                options.add_argument(f"--user-data-dir={edge_data}")
                options.add_argument("--profile-directory=AutoCourse")
        try:
            self.driver = webdriver.Edge(options=options)
        except Exception:
            print("正在尝试自动安装 EdgeDriver...")
            try:
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                service = EdgeService(EdgeChromiumDriverManager().install())
                self.driver = webdriver.Edge(service=service, options=options)
            except ImportError:
                print("请安装 webdriver_manager: pip install webdriver-manager")
                raise
        self._apply_anti_detection()

    def _apply_anti_detection(self):
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            }
        )
        self.driver.implicitly_wait(10)
        return self.driver

    def wait_for_element(self, by, value, timeout=30):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def wait_for_clickable(self, by, value, timeout=30):
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    def switch_to_new_tab(self):
        self.driver.switch_to.window(self.driver.window_handles[-1])

    def switch_to_default_tab(self):
        self.driver.switch_to.window(self.driver.window_handles[0])

    def close_other_tabs(self):
        handles = self.driver.window_handles
        for handle in handles[1:]:
            self.driver.switch_to.window(handle)
            self.driver.close()
        self.driver.switch_to.window(handles[0])

    def scroll_to_bottom(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    def scroll_to_element(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element
        )
        time.sleep(0.5)

    def safe_click(self, element):
        self.scroll_to_element(element)
        time.sleep(0.3)
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
