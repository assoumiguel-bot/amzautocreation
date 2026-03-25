import asyncio
import re
from playwright.async_api import async_playwright

EMAIL = "JacquelineKap8546@hotmail.com"
PASSWORD = "Qpf6Q5C1w"

async def test():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=False, channel="chrome")
        except Exception:
            browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        print("1. Goto login.live.com...")
        await page.goto("https://login.live.com/", wait_until="domcontentloaded")

        print("2. Email...")
        email_input = page.locator("#usernameEntry, #i0116, input[type='email'], input[name='loginfmt']").first
        await email_input.wait_for(state="visible", timeout=10000)
        await email_input.click()
        await page.wait_for_timeout(200)
        await page.keyboard.type(EMAIL, delay=80)
        print(f"   OK: {EMAIL}")

        await page.wait_for_timeout(400)
        suivant = page.locator("#idSIButton9, input[type='submit'], button[type='submit']").first
        await suivant.wait_for(state="visible", timeout=8000)
        await suivant.click()
        print("   Suivant clicked.")
        await page.wait_for_timeout(4000)

        print("3. Password...")
        pw = page.locator("#i0118, input[type='password'], input[name='passwd']").first
        await pw.wait_for(state="visible", timeout=12000)
        await pw.click()
        await page.wait_for_timeout(200)
        await page.keyboard.type(PASSWORD, delay=80)
        print("   Password OK.")

        await page.wait_for_timeout(400)
        btn = page.locator("#idSIButton9, input[type='submit'], button[type='submit']").first
        await btn.wait_for(state="visible", timeout=8000)
        try:
            await btn.click(timeout=8000, no_wait_after=True)
        except Exception:
            pass
        print("   Se connecter clicked.")
        await page.wait_for_timeout(8000)

        try:
            await page.locator("#idBtn_Back").click(timeout=3000)
        except Exception:
            pass

        print("4. Inbox...")
        await page.goto("https://outlook.live.com/mail/0/inbox", wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(10000)
        print(f"   URL: {page.url}")

        print("5. Amazon email...")
        rows = await page.query_selector_all("div[role='listitem'], div[role='option'], [data-convid]")
        print(f"   Rows found: {len(rows)}")
        for row in rows[:15]:
            try:
                txt = await row.text_content()
                if txt and ("amazon" in txt.lower() or "verify" in txt.lower()):
                    await row.click()
                    print(f"   Clicked: {txt[:60].strip()}")
                    await page.wait_for_timeout(5000)
                    break
            except Exception:
                continue

        body = await page.inner_text("body")
        otp = re.findall(r"\b\d{6}\b", body)
        print(f"   OTP: {otp[0] if otp else 'MAWJOUDCH'}")
        print("DONE!")
        await page.wait_for_timeout(5000)
        await browser.close()

asyncio.run(test())
