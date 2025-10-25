"""Scraper logic: contains the Playwright `run` function extracted from `app.py`.

This module focuses on the page automation and extracting a brief
summary from the loaded Groupon page.
"""

from typing import Optional
import json

from playwright.async_api import Page


SORT_OPTIONS = ["relevance", "price:asc", "price:desc", "distance", "rating"]


async def run(
    page: Page,
    query: str,
    sort_option: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
) -> dict | None:
    overlay_offer_loc = page.locator('[data-bhw="ExitBannerModal"]')
    search_box_loc = page.get_by_test_id("search-input")
    sort_filter_box_loc = page.locator('[data-bhw="sort-filter-box"]').first
    select_sort_filter_loc = page.locator(f'[data-bhc="sort:{sort_option}"]')
    price_range_loc = page.get_by_test_id("filter-section-price").get_by_role("textbox")
    item_list_loc = page.get_by_test_id("deal-grid").first

    await page.add_locator_handler(
        overlay_offer_loc, lambda offer: offer.get_by_role("button").click()
    )

    await page.goto("https://www.groupon.com/")
    await search_box_loc.wait_for()
    await search_box_loc.fill(query)
    await search_box_loc.press("Enter")
    await sort_filter_box_loc.wait_for()

    # Set sort filter
    sort_option = (sort_option or "").lower()
    if sort_option in SORT_OPTIONS:
        await sort_filter_box_loc.click()
        await select_sort_filter_loc.click()

    # Set price range
    if price_min:
        await price_range_loc.first.fill(str(price_min))
        await price_range_loc.first.press("Tab")

    if price_max:
        await price_range_loc.last.fill(str(price_max))
        await price_range_loc.last.press("Tab")

    # Grab the first item
    await item_list_loc.wait_for()
    notfound = await page.locator('[data-bhw="EmptyDealList"]').count() != 0
    if notfound:
        return

    first_item_info = (
        await page.get_by_test_id("deal-grid")
        .locator("a")
        .first.get_attribute("data-bhd")
    ) or ""

    info_dict = json.loads(first_item_info)
    section1 = info_dict["body"]["section1"]["content"]
    section2 = info_dict["body"]["section2"]["content"]
    section3 = info_dict["body"]["section3"]["content"]
    brief_info_dict = {
        "name": section1,
        "prices": {
            "list_price": section2["list_price"],
            "sell_price": section2["sell_price"],
            "discount": section2["discount"],
            "isocode_currency": section2["isocode_currency"],
            "currency_exponent": section2["currency_exponent"],
        },
        "supplier": section3,
    }

    return brief_info_dict
