# publish_medium.py
import os, time, json, glob, argparse, random
from pathlib import Path
from helpers import save_cookies_to_file, load_cookies_from_file, human_typing_send_keys, split_to_sentences, append_to_log
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

COOKIE_FILE = "cookies.pkl"
OUTBOX = "outbox"
LOGFILE = "posts_log.csv"

def get_driver():
    # prefer undetected_chromedriver if available
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
        # set a common user-agent
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        return driver

def load_and_apply_cookies(driver, cookie_path=COOKIE_FILE):
    import pickle
    if not os.path.exists(cookie_path):
        raise FileNotFoundError("Cookies file not found. Run save_cookies.py first.")
    with open(cookie_path, "rb") as f:
        cookies = pickle.load(f)
    driver.get("https://medium.com/")
    time.sleep(2)
    for c in cookies:
        cookie = {k:c[k] for k in c if k not in ("sameSite",)}
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print("[publisher] Warning adding cookie:", e)
    driver.refresh()
    time.sleep(3)

def find_contenteditable_nodes(driver):
    # return list of elements that are contenteditable
    script = "return Array.from(document.querySelectorAll('[contenteditable=\"true\"]'));"
    nodes = driver.execute_script(script)
    # the returned nodes are WebElement proxies; we fetch with find_elements as fallback
    els = driver.find_elements(By.CSS_SELECTOR, '[contenteditable="true"]')
    return els

def set_title_and_body_by_typing(driver, title, body, typing_wpm=40):
    """
    Locate Medium's title + body fields and type the article.
    Uses multiple fallback selectors since Medium's DOM changes often.
    """
    wait = WebDriverWait(driver, 15)

    # --- TITLE ---
    try:
        title_box = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "h1[contenteditable='true'], "
            "h1.graf--title, "
            "h1[placeholder='Title'], "
            "section div[data-placeholder='Title']"
        )))
    except Exception as e:
        print("[DEBUG] Could not locate title. Dumping first 2000 chars of page HTML:")
        print(driver.page_source[:2000])
        raise RuntimeError(f"Could not find the title field: {e}")

    title_box.click()
    time.sleep(0.3)
    title_box.send_keys(Keys.CONTROL, "a")
    title_box.send_keys(Keys.DELETE)
    human_typing_send_keys(title_box, title, wpm=typing_wpm)
    time.sleep(random.uniform(0.5, 1.2))

    # --- BODY ---
    try:
        body_box = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "article div[contenteditable='true'], "
            "section div[contenteditable='true'], "
            "div[role='textbox']"
        )))
    except Exception as e:
        print("[DEBUG] Could not locate body. Dumping first 2000 chars of page HTML:")
        print(driver.page_source[:2000])
        raise RuntimeError(f"Could not find the body field: {e}")

    body_box.click()
    time.sleep(0.3)
    body_box.send_keys(Keys.CONTROL, "a")
    body_box.send_keys(Keys.DELETE)

    # --- TYPE ARTICLE ---
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    for p in paragraphs:
        sentences = split_to_sentences(p)
        for s in sentences:
            human_typing_send_keys(body_box, s, wpm=typing_wpm)
            body_box.send_keys(" ")
            time.sleep(random.uniform(0.05, 0.18))
        body_box.send_keys(Keys.ENTER)
        body_box.send_keys(Keys.ENTER)
        time.sleep(random.uniform(0.2, 0.6))
        
def click_publish_flow(driver, confirm_publish=True):
    time.sleep(1)
    # Click "Publish" or "Publish" button in UI
    # Buttons can vary; try a few selectors
    clicked = False
    # strategy: find button elements and match visible text
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for b in buttons:
            try:
                txt = b.text.strip().lower()
            except Exception:
                txt = ""
            if "publish" in txt and len(txt) < 30:
                b.click()
                clicked = True
                break
    except Exception:
        pass

    if not clicked:
        # fallback: keyboard shortcut (Ctrl+Enter usually works)
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.CONTROL, Keys.ENTER)
            clicked = True
        except Exception:
            pass

    time.sleep(2)
    if confirm_publish:
        # After clicking, Medium shows publish modal with options; try to click final publish
        try:
            # look for button with text like "Publish now" or "Publish"
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for b in buttons:
                try:
                    txt = b.text.strip().lower()
                except Exception:
                    txt = ""
                if "publish now" in txt or "publish" == txt:
                    b.click()
                    time.sleep(2)
                    return True
        except Exception:
            pass
    return clicked

def pick_latest_outbox_json():
    files = sorted(glob.glob(os.path.join(OUTBOX, "*.json")), reverse=True)
    if not files:
        raise FileNotFoundError("No generated article found in outbox/. Run generator.py first.")
    return files[0]

def publish_article(dry_run=True, typing_wpm=40, publish_confirm=False):
    # load latest article
    f = pick_latest_outbox_json()
    with open(f, "r", encoding="utf-8") as fh:
        j = json.load(fh)
    title = j.get("title", f"Automated post {time.strftime('%Y-%m-%d')}")
    body = j.get("body_markdown", "This is a test post.")

    driver = get_driver()
    try:
        load_and_apply_cookies(driver, COOKIE_FILE)
        # go to new story editor
        driver.get("https://medium.com/new-story")
        time.sleep(5 + random.uniform(0.5,1.5))
        # set title and body by typing
        set_title_and_body_by_typing(driver, title, body, typing_wpm=typing_wpm)
        time.sleep(1)
        if dry_run:
            print("[publish] Dry run mode - not clicking publish. Inspect the browser manually.")
            # save a small screenshot for debugging
            try:
                ss = "last_dryrun.png"
                driver.save_screenshot(ss)
                print("[publish] Saved screenshot to", ss)
            except Exception:
                pass
            result_url = None
            status = "dry-run"
        else:
            ok = click_publish_flow(driver, confirm_publish=publish_confirm)
            if not ok:
                status = "publish-click-failed"
                result_url = None
            else:
                # wait a bit then try to capture the current URL or confirmation
                time.sleep(4)
                try:
                    url = driver.current_url
                except Exception:
                    url = None
                status = "published" if url else "unknown"
                result_url = url
        # append to logfile
        row = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "title": title, "status": status, "url": result_url or ""}
        append_to_log(LOGFILE, row)
        print("[publish] Logged:", row)
        return row
    finally:
        # keep browser open a short time for you to inspect if dry-run, else close
        print("[publish] Closing browser in 8 seconds...")
        time.sleep(8)
        driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="Actually click Publish (default is dry-run).")
    parser.add_argument("--wpm", type=int, default=40, help="Typing speed in words per minute.")
    parser.add_argument("--confirm", action="store_true", help="Confirm the final publish modal (may cause extra clicks).")
    args = parser.parse_args()
    publish_article(dry_run=not args.publish, typing_wpm=args.wpm, publish_confirm=args.confirm)
