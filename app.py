import re
from playwright.sync_api import Playwright, sync_playwright, Page


def process(page: Page):
    # Start point
    page.goto("https://www.lenovo.com/us/en/")

    # Search
    searchbar = page.locator("#commonHeaderSearch")
    searchbar.fill("thinkpad")
    searchbar.press("Enter")
    page.wait_for_load_state("domcontentloaded")

    # Filter
    amd_filter = re.compile(r"All AMD Processors\d+")
    page.get_by_role("checkbox", name=amd_filter).click()
    page.wait_for_load_state("domcontentloaded")

    # Sorting
    page.locator("#dlp_sort").click()
    page.locator("#dlp_sort_bestSelling").click()
    page.wait_for_load_state("domcontentloaded")

    # Navigate to the first item info page
    page.wait_for_selector(".product_list", timeout=10000)
    page.locator(
        '.product_list [data-align-index="0"][data-align-group="0"] .product_title a'
    ).click()

    # Grab basic info
    infoPairs: dict[str, str] = {}
    page.wait_for_selector("h1.product_summary", timeout=10000)
    infoPairs["Product Name"] = page.locator("h1.product_summary").inner_text()
    infoPairs["Part Number"] = page.locator(".part_number").inner_text().split(":")[-1]
    infoPairs["Price"] = page.locator(".price-title").inner_text()

    # Grab specs info
    specGroups = page.locator(".system_specs_container .specs_item .normal_specs").all()
    for group in specGroups:
        name = group.locator(".item_name").inner_text()
        content = group.locator(".item_content").inner_text()
        infoPairs[name] = content

    # Output
    print("\n" + "=" * 60)
    for name, content in infoPairs.items():
        ctn = content.replace("\n", " | ").strip()
        print(f"{name:20}{ctn}")
    print("=" * 60)

    # Success message
    print(
        f"\n✅ Success! Product '{infoPairs["Product Name"]}' found and specs extracted.\n"
    )


def run(playwright: Playwright) -> None:
    # Init
    browser = playwright.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    # Handler: Kill offer overlays
    closeOfferButton = page.get_by_role("button", name="Decline Offer")
    page.add_locator_handler(closeOfferButton, lambda btn: btn.click())

    # Start processing
    print("Looking for specs of the best selling AMD ThinkPad...")
    try:
        process(page)
    except TimeoutError as e:
        print(f"❌ Operation failed: An element was not found in time.")
        print(f"   Details: {e}")
        page.screenshot(path="error_screenshot.png")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        page.screenshot(path="error_screenshot.png")
    finally:
        # Clean up
        context.close()
        browser.close()


with sync_playwright() as playwright:
    run(playwright)
