"""Test: fills Amazon Developer Console registration form.
   Uses exact element IDs from the real page."""
import asyncio
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# === TEST DATA ===
EMAIL = "CodyHogan9441@outlook.com"
PASSWORD = "msldf2254981"
COUNTRY = "United States"
BUSINESS = "Cody Hogan"
ADDRESS = "123 Main Street"
CITY = "New York"
STATE = "New York"
ZIP_CODE = "10001"
PHONE = "5551234567"
PHONE_CC = "1"  # without +
# =================

async def human_type(page, selector, text):
    el = page.locator(selector).first
    await el.click()
    await page.wait_for_timeout(200)
    for char in text:
        await page.keyboard.type(char)
        await page.wait_for_timeout(random.randint(60, 150))

async def main():
    from playwright.async_api import async_playwright

    p = await async_playwright().start()
    print("Launching Chrome...", flush=True)
    try:
        browser = await p.chromium.launch(headless=False, channel="chrome")
    except Exception:
        browser = await p.chromium.launch(headless=False)

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = await context.new_page()

    # === Login to Amazon ===
    print("1. Going to Amazon Developer Console...", flush=True)
    await page.goto("https://developer.amazon.com/settings/console/registration", wait_until="domcontentloaded", timeout=40000)
    await page.wait_for_timeout(3000)

    if "login" in page.url or "signin" in page.url or "ap/" in page.url:
        print("2. Login required...", flush=True)
        for sel in ["#ap_email", "input[type='email']"]:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    await human_type(page, sel, EMAIL)
                    break
            except Exception:
                continue
        await page.wait_for_timeout(500)
        for sel in ["#continue", "input[type='submit']"]:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    await el.click()
                    break
            except Exception:
                continue
        await page.wait_for_timeout(3000)
        for sel in ["#ap_password", "input[type='password']"]:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    await human_type(page, sel, PASSWORD)
                    break
            except Exception:
                continue
        await page.wait_for_timeout(500)
        for sel in ["#signInSubmit", "input[type='submit']"]:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    await el.click()
                    break
            except Exception:
                continue
        await page.wait_for_timeout(8000)
        print(f"   Logged in. URL: {page.url}", flush=True)

        if "registration" not in page.url:
            await page.goto("https://developer.amazon.com/settings/console/registration", wait_until="domcontentloaded", timeout=40000)
            await page.wait_for_timeout(4000)

    print(f"3. On page: {page.url}", flush=True)
    await page.wait_for_timeout(3000)

    print("4. Filling form with exact IDs...", flush=True)

    # === COUNTRY (custom dropdown inside div#country_code) ===
    try:
        country_input = page.locator("#country_code input").first
        await country_input.scroll_into_view_if_needed()
        await country_input.click()
        await page.wait_for_timeout(500)
        await page.keyboard.type(COUNTRY, delay=50)
        await page.wait_for_timeout(1000)
        # Real mouse click on the option
        option = page.locator(f"div[title='{COUNTRY}']").first
        box = await option.bounding_box()
        if box:
            await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        print(f"   [OK] Country: {COUNTRY}", flush=True)
        await page.wait_for_timeout(500)
    except Exception as e:
        print(f"   [FAIL] Country: {e}", flush=True)

    # === BUSINESS NAME (id='company_name') ===
    try:
        await page.locator("#company_name").scroll_into_view_if_needed()
        await page.locator("#company_name").click()
        await page.wait_for_timeout(200)
        await page.keyboard.type(BUSINESS, delay=60)
        print(f"   [OK] Business: {BUSINESS}", flush=True)
    except Exception as e:
        print(f"   [FAIL] Business: {e}", flush=True)
    await page.wait_for_timeout(300)

    # === ADDRESS LINE 1 (id='address_line') ===
    try:
        await page.locator("#address_line").scroll_into_view_if_needed()
        await page.locator("#address_line").click()
        await page.wait_for_timeout(200)
        await page.keyboard.type(ADDRESS, delay=60)
        print(f"   [OK] Address: {ADDRESS}", flush=True)
    except Exception as e:
        print(f"   [FAIL] Address: {e}", flush=True)
    await page.wait_for_timeout(300)

    # === CITY (id='city') ===
    try:
        await page.locator("#city").scroll_into_view_if_needed()
        await page.locator("#city").click()
        await page.wait_for_timeout(200)
        await page.keyboard.type(CITY, delay=60)
        print(f"   [OK] City: {CITY}", flush=True)
    except Exception as e:
        print(f"   [FAIL] City: {e}", flush=True)
    await page.wait_for_timeout(300)

    # === POSTAL CODE (id='postal_code') ===
    try:
        await page.locator("#postal_code").scroll_into_view_if_needed()
        await page.locator("#postal_code").click()
        await page.wait_for_timeout(200)
        await page.keyboard.type(ZIP_CODE, delay=60)
        print(f"   [OK] Postal: {ZIP_CODE}", flush=True)
    except Exception as e:
        print(f"   [FAIL] Postal: {e}", flush=True)
    await page.wait_for_timeout(300)

    # === STATE (custom dropdown - same approach as Country/Phone CC) ===
    try:
        state_input = page.locator("#state").first
        await state_input.scroll_into_view_if_needed()
        await state_input.click()
        await page.wait_for_timeout(800)
        await page.keyboard.type(STATE, delay=50)
        await page.wait_for_timeout(1500)
        # Get the parent container of #state, then find the option INSIDE it
        # Use value='NY' which is unique to state options (not country/CC)
        # Use value attribute to target ONLY the state option (not country/CC)
        state_option = page.locator(f"div[value='NY'][title='{STATE}']").first
        await state_option.dispatch_event("mousedown")
        await page.wait_for_timeout(500)
        print(f"   [OK] State: {STATE}", flush=True)
    except Exception as e:
        print(f"   [FAIL] State: {e}", flush=True)
    await page.wait_for_timeout(300)

    # === SAME AS PRIMARY EMAIL (id='ckbx_company_sup_email') ===
    try:
        # Custom checkbox - use JavaScript click since it may be visually hidden
        cb = page.locator("#ckbx_company_sup_email")
        await cb.scroll_into_view_if_needed()
        await cb.evaluate("el => el.click()")
        print("   [OK] Same as primary email: checked", flush=True)
    except Exception as e:
        # Try clicking the label instead
        try:
            await page.locator("text=Same as primary email address").click()
            print("   [OK] Same as primary email: checked (via label)", flush=True)
        except Exception as e2:
            print(f"   [FAIL] Same as primary: {e2}", flush=True)
    await page.wait_for_timeout(300)

    # === PHONE CC (custom dropdown with placeholder '- CC -') ===
    try:
        cc_input = page.locator("input[placeholder='- CC -']").first
        await cc_input.scroll_into_view_if_needed()
        await cc_input.click()
        await page.wait_for_timeout(800)
        # Type "us" to filter
        await page.keyboard.type("us", delay=80)
        await page.wait_for_timeout(1500)
        # Dispatch mousedown event (React listens on mousedown, not click)
        await page.locator("div[title='US (+1)']").first.dispatch_event("mousedown")
        await page.wait_for_timeout(300)
        await page.locator("div[title='US (+1)']").first.dispatch_event("mouseup")
        await page.wait_for_timeout(300)
        print(f"   [OK] Phone CC: US (+1) (mousedown)", flush=True)
        await page.wait_for_timeout(500)
    except Exception as e:
        print(f"   [FAIL] Phone CC: {e}", flush=True)
    await page.wait_for_timeout(300)

    # === PHONE NUMBER (id='company_phone') ===
    try:
        await page.locator("#company_phone").scroll_into_view_if_needed()
        await page.locator("#company_phone").click()
        await page.wait_for_timeout(200)
        await page.keyboard.type(PHONE, delay=60)
        print(f"   [OK] Phone: {PHONE}", flush=True)
    except Exception as e:
        print(f"   [FAIL] Phone: {e}", flush=True)
    await page.wait_for_timeout(300)

    # === INTEREST: "Developing apps and games" (id='ckbx_registration_app_store_opt_in') ===
    try:
        cb = page.locator("#ckbx_registration_app_store_opt_in")
        await cb.scroll_into_view_if_needed()
        await cb.evaluate("el => el.click()")
        print("   [OK] Interest: Developing apps checked", flush=True)
    except Exception as e:
        try:
            await page.locator("text=Developing apps and games").click()
            print("   [OK] Interest: Developing apps checked (via label)", flush=True)
        except Exception:
            print(f"   [FAIL] Interest: {e}", flush=True)
    await page.wait_for_timeout(300)

    # Screenshot
    try:
        await page.screenshot(path=os.path.join(BASE_DIR, "dev_console_after.png"), full_page=True)
        print("   Screenshot: dev_console_after.png", flush=True)
    except Exception:
        pass

    # === CLICK "Agree and Continue" ===
    try:
        await page.wait_for_timeout(1000)
        agree_btn = page.locator("button:has-text('Agree and Continue')").first
        await agree_btn.scroll_into_view_if_needed()
        await agree_btn.click()
        print("   [OK] Clicked 'Agree and Continue'", flush=True)
        await page.wait_for_timeout(5000)
        print(f"   URL after submit: {page.url}", flush=True)
    except Exception as e:
        print(f"   [FAIL] Agree and Continue: {e}", flush=True)

    print("\n=== DONE === Check browser. Close Chrome when done.", flush=True)

    try:
        while browser.is_connected():
            await asyncio.sleep(1)
    except Exception:
        pass
    await p.stop()

if __name__ == "__main__":
    asyncio.run(main())
