# helpers.py
import os, time, pickle, random, json
from pathlib import Path

# Cookie helpers
def save_cookies_to_file(driver, filepath="cookies.pkl"):
    cookies = driver.get_cookies()
    with open(filepath, "wb") as f:
        pickle.dump(cookies, f)
    print(f"[helpers] Saved {len(cookies)} cookies to {filepath}")

def load_cookies_from_file(driver, filepath="cookies.pkl"):
    import pickle
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cookie file not found: {filepath}")
    with open(filepath, "rb") as f:
        cookies = pickle.load(f)
    # ensure on base domain first
    return cookies

# Human typing simulation
def human_typing_send_keys(element, text, wpm=40, variance=0.25):
    """
    Simulate human typing into a Selenium element.
    wpm: words-per-minute baseline (words counted as 5 chars)
    variance: fractional random variation applied to the wpm to make speed non-uniform
    """
    # compute average delay per character
    # words-per-minute -> chars-per-second: (wpm * 5) / 60
    cps = (wpm * 5) / 60.0
    # char delay in seconds
    base_delay = 1.0 / max(0.1, cps)
    # We'll type sentence-by-sentence to allow pauses
    sentences = split_to_sentences(text)
    for s in sentences:
        # small chance to make a typo and correct (optional realism)
        for ch in s:
            # apply variance
            v = (1.0 + random.uniform(-variance, variance))
            delay = max(0.01, base_delay * v)
            element.send_keys(ch)
            time.sleep(delay)
        # after sentence pause
        time.sleep(random.uniform(0.15, 0.5))

def split_to_sentences(text):
    # naive split on double newlines and sentence punctuation
    parts = []
    # first split by paragraphs
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        # split into small sentences by punctuation but keep them reasonably sized
        import re
        sentences = re.split(r'(?<=[\.\?\!])\s+', para)
        parts.extend(sentences)
    return parts

# simple logger
def append_to_log(logfile, row: dict):
    import csv
    file_exists = os.path.exists(logfile)
    with open(logfile, "a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    