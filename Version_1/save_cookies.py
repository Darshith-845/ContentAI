# save_cookies.py
"""
Run this once on the machine where you'll run automation.
It opens a real browser. You log in to Medium manually.
After login, press Enter in the terminal to save cookies.
"""
import time, pickle
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def get_driver():
    # try undetected_chromedriver for stealth
    try:
        import undetected_chromedriver as uc
        opts = uc.ChromeOptions()
        opts.add_argument("--start-maximized")
        driver = uc.Chrome(options=opts)
        return driver
    except Exception:
        from selenium.webdriver.chrome.options import Options
        opts = Options()
        opts.add_argument("--start-maximized")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        return driver

def save_cookies_interactive(cookie_path="cookies.pkl"):
    driver = get_driver()
    try:
        driver.get("https://medium.com/")
        print("Browser opened. Please sign in to Medium manually in the opened browser.")
        input("After you are signed in and the homepage shows your profile, press Enter here to save cookies...")
        time.sleep(1)
        cookies = driver.get_cookies()
        with open(cookie_path, "wb") as f:
            pickle.dump(cookies, f)
        print(f"Saved {len(cookies)} cookies to {cookie_path}")
    finally:
        driver.quit()

if __name__ == "__main__":
    save_cookies_interactive()

