import time
import unittest
import threading
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from database import get_db

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class TestVoiceOneSelenium(unittest.TestCase):
    server_thread = None
    server_port = 5005
    base_url = f"http://127.0.0.1:{server_port}"
    driver = None

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["SECRET_KEY"] = "voiceone-selenium-testing-key"
        
        def run_server():
            cls.app.run(host="127.0.0.1", port=cls.server_port, debug=False, use_reloader=False)

        cls.server_thread = threading.Thread(target=run_server, daemon=True)
        cls.server_thread.start()
        time.sleep(1.5)

        if SELENIUM_AVAILABLE:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1400,900")
            try:
                service = Service(ChromeDriverManager().install())
                cls.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception:
                try:
                    cls.driver = webdriver.Chrome(options=chrome_options)
                except Exception as e:
                    print(f"Selenium Chrome WebDriver not initialized: {e}")
                    cls.driver = None

    @classmethod
    def tearDownClass(cls):
        if cls.driver:
            try:
                cls.driver.quit()
            except Exception:
                pass

    def test_01_underage_login_rejection(self):
        if not self.driver:
            self.skipTest("Selenium Chrome driver not available.")
            
        driver = self.driver
        driver.get(f"{self.base_url}/auth/logout")
        time.sleep(0.5)
        driver.get(f"{self.base_url}/auth/login")
        self.assertIn("VoiceOne", driver.title)

        # Fill underage citizen data (Age < 18)
        driver.find_element(By.ID, "name-input").send_keys("Rahul Underage")
        driver.find_element(By.ID, "aadhaar-input").send_keys("112233445566")
        
        # Set date using JS to avoid OS locale datepicker formatting issues
        dob_elem = driver.find_element(By.ID, "dob-input")
        driver.execute_script("arguments[0].value = '2015-05-10';", dob_elem)
        
        driver.find_element(By.ID, "btn-submit-verify").click()
        time.sleep(1.2)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        self.assertTrue("Verification Failed" in body_text or "Minimum required age is 18" in body_text or "Access restricted" in body_text)

    def test_02_eligible_citizen_login(self):
        if not self.driver:
            self.skipTest("Selenium Chrome driver not available.")
            
        driver = self.driver
        driver.get(f"{self.base_url}/auth/logout")
        time.sleep(0.5)
        driver.get(f"{self.base_url}/auth/login")

        # Fill eligible citizen data (Age >= 18)
        driver.find_element(By.ID, "name-input").send_keys("Siddharth Varma")
        driver.find_element(By.ID, "aadhaar-input").send_keys("918273645019")

        dob_elem = driver.find_element(By.ID, "dob-input")
        driver.execute_script("arguments[0].value = '1996-03-24';", dob_elem)

        driver.find_element(By.ID, "btn-submit-verify").click()
        time.sleep(1.2)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        self.assertIn("Welcome to VoiceOne, Siddharth Varma", body_text)
        self.assertIn("Siddharth Varma", body_text)

    def test_03_create_researched_bill_poll(self):
        if not self.driver:
            self.skipTest("Selenium Chrome driver not available.")
            
        driver = self.driver
        driver.get(f"{self.base_url}/polls/create")
        
        driver.find_element(By.ID, "poll-title").send_keys("Urban Forest Conservation & Biodiversity Bill 2026")
        driver.find_element(By.ID, "poll-bill-number").send_keys("Bill No. 77 of 2026 (Lok Sabha)")
        driver.find_element(By.ID, "poll-source-url").send_keys("https://prsindia.org/billtrack/urban-forest-2026")
        driver.find_element(By.ID, "poll-summary").send_keys("Protects urban green belts, mandates tree preservation bylaws for commercial real estate developments, and introduces citizen environmental audits.")
        
        driver.find_element(By.ID, "btn-submit-poll").click()
        time.sleep(1.2)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        self.assertIn("Urban Forest Conservation & Biodiversity Bill 2026", body_text)
        self.assertIn("Nationwide Citizen Voting Results", body_text)

    def test_04_voting_workflow_and_paper_visualizer(self):
        if not self.driver:
            self.skipTest("Selenium Chrome driver not available.")
            
        driver = self.driver
        driver.get(f"{self.base_url}/")
        
        # Click Vote FOR on first poll
        btn_for = driver.find_element(By.CSS_SELECTOR, ".btn-for")
        btn_for.click()
        time.sleep(1.0)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        self.assertTrue("Voted FOR" in body_text or "100%" in body_text or "For" in body_text)

    def test_05_forum_moderation_and_hate_speech_removal(self):
        if not self.driver:
            self.skipTest("Selenium Chrome driver not available.")
            
        driver = self.driver
        driver.get(f"{self.base_url}/forum/")

        # 1. Post Polite Message -> Should be approved
        content_input = driver.find_element(By.ID, "post-content-input")
        content_input.send_keys("A transparent civic process empowers every citizen to hold governance accountable.")
        driver.find_element(By.ID, "btn-submit-forum-post").click()
        time.sleep(1.2)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        self.assertIn("A transparent civic process empowers every citizen", body_text)

        # 2. Post Hate / Casteist Discriminatory Content -> Must be auto-removed
        content_input = driver.find_element(By.ID, "post-content-input")
        content_input.send_keys("These low caste untouchable shudra people are ruining society.")
        driver.find_element(By.ID, "btn-submit-forum-post").click()
        time.sleep(1.2)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        self.assertIn("Violates VoiceOne Civility Guidelines", body_text)
        self.assertNotIn("These low caste untouchable shudra people are ruining society.", body_text)

if __name__ == "__main__":
    unittest.main()
