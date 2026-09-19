import csv
import os
import re
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


URL = (
    "https://www.virginatlantic.com/holidays/options/holiday/"
    "international-drive/sonesta-es-suites-orlando---international-drive/hotel"
    "?CTA=AbTest_SP_Holidays"
    "&departureDate=15-12-2027"
    "&duration=14"
    "&gateway=LHR"
    "&room=a2%2Cc4%2Cc7%2Ci2"
)

HISTORY_FILE = "price_history.csv"


def extract_price(page):
    # Look for common Virgin price formats such as £4,123 or £4123.
    text = page.locator("body").inner_text()

    prices = re.findall(r"£\s?[\d,]+(?:\.\d{2})?", text)

    values = []

    for price in prices:
        number = price.replace("£", "").replace(",", "").strip()

        try:
            value = float(number)
            if value > 500:
                values.append(value)
        except ValueError:
            pass

    if not values:
        raise RuntimeError("No suitable holiday price was found.")

    # The cheapest package price shown on the page.
    return min(values)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={"width": 1440, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        print("Opening Virgin Holidays...")

        page.goto(URL, wait_until="domcontentloaded", timeout=120000)

        # Give Virgin's dynamic booking system time to load.
        page.wait_for_timeout(15000)

        print("Reading holiday price...")

        price = extract_price(page)

        now = datetime.now(timezone.utc).astimezone()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        print(f"Price found: £{price:,.2f}")

        file_exists = os.path.exists(HISTORY_FILE)

        with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            if not file_exists:
                writer.writerow(["timestamp", "price"])

            writer.writerow([timestamp, f"{price:.2f}"])

        browser.close()


if _name_ == "_main_":
    main()
