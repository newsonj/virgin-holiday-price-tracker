import csv
import os
import re
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


URL = (
    "https://www.virginatlantic.com/holidays/search/holiday/"
    "international-drive"
    "?CTA=AbTest_SP_Holidays"
    "&duration=14"
    "&gateway=LHR"
    "&room=a2%2Cc4%2Cc7%2Ci2"
    "&departureDate=14-12-2027"
)

TARGET_HOTEL = "Sonesta ES Suites Orlando - International Drive"
HISTORY_FILE = "price_history.csv"


def money_to_float(value):
    return float(
        value.replace("£", "")
        .replace(",", "")
        .strip()
    )


def find_target_card(page):
    """
    Find the smallest page element containing:
    - Sonesta hotel name
    - a per-person price
    - a total price
    """

    return page.locator("body *").evaluate_all(
        """
        (elements, targetHotel) => {

            const candidates = [];

            for (const element of elements) {

                const text = (element.innerText || "").trim();

                if (!text.includes(targetHotel)) {
                    continue;
                }

                const hasPP =
                    /£\\s?[\\d,]+(?:\\.\\d{2})?\\s*pp\\b/i.test(text);

                const hasTotal =
                    /Total\\s+price\\s*£\\s?[\\d,]+(?:\\.\\d{2})?/i.test(text);

                if (hasPP && hasTotal) {
                    candidates.push({
                        text: text,
                        length: text.length
                    });
                }
            }

            if (candidates.length === 0) {
                return null;
            }

            candidates.sort((a, b) => a.length - b.length);

            return candidates[0].text;
        }
        """,
        TARGET_HOTEL
    )


def save_price_history(total_price, price_pp):

    file_exists = os.path.exists(HISTORY_FILE)

    with open(
        HISTORY_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "hotel",
                "price_pp",
                "total_price"
            ])

        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            TARGET_HOTEL,
            price_pp,
            total_price
        ])


with sync_playwright() as p:

    print("=" * 60)
    print("VIRGIN HOLIDAY PRICE CHECK")
    print("=" * 60)

    print()
    print("Opening Virgin Holidays...")

    browser = p.chromium.launch(
        headless=True
    )

    page = browser.new_page(
        viewport={
            "width": 1440,
            "height": 1000
        }
    )

    page.goto(
        URL,
        wait_until="domcontentloaded",
        timeout=120000
    )

    print("Waiting for Virgin Holidays prices...")

    page.wait_for_timeout(30000)

    print("Looking for target hotel...")

    target_card_text = find_target_card(page)

    if not target_card_text:

        print()
        print("=" * 60)
        print("ERROR - TARGET HOTEL CARD NOT FOUND")
        print("=" * 60)
        print()
        print(TARGET_HOTEL)
        print()
        print("The script will NOT guess a price.")

        browser.close()

        raise SystemExit(1)

    pp_match = re.search(
        r"£\s?([\d,]+(?:\.\d{2})?)\s*pp\b",
        target_card_text,
        re.IGNORECASE
    )

    total_match = re.search(
        r"Total\s+price\s*£\s?([\d,]+(?:\.\d{2})?)",
        target_card_text,
        re.IGNORECASE
    )

    if not pp_match or not total_match:

        print()
        print("=" * 60)
        print("ERROR - PRICE NOT FOUND")
        print("=" * 60)
        print()
        print("The hotel was found, but the expected prices")
        print("could not be extracted.")
        print()
        print("The script will NOT guess a price.")

        browser.close()

        raise SystemExit(1)

    price_pp = money_to_float(
        pp_match.group(1)
    )

    total_price = money_to_float(
        total_match.group(1)
    )

    print()
    print("=" * 60)
    print("TARGET HOTEL PRICE")
    print("=" * 60)

    print()
    print(f"Hotel: {TARGET_HOTEL}")
    print(f"Price per person: £{price_pp:,.2f}")
    print(f"Total price: £{total_price:,.2f}")

    save_price_history(
        total_price,
        price_pp
    )

    print()
    print("Price saved to price_history.csv")

    print()
    print("=" * 60)
    print("CHECK COMPLETE")
    print("=" * 60)

    browser.close()
