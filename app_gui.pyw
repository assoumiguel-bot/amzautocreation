import tkinter as tk
import tkinter.simpledialog
from tkinter import ttk, messagebox, filedialog
import threading
import time
import re
import random
import subprocess
import os
import sys
import asyncio

if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

COUNTRIES = [
    "United Kingdom", "Germany", "France", "Netherlands",
    "Canada", "Australia", "Japan", "Spain", "Italy", "Brazil", "India",
    "Singapore", "Sweden", "Switzerland", "Belgium", "Poland", "Turkey"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROTON_VPN_EXE = r"C:\Program Files\Proton\VPN\ProtonVPN.Launcher.exe"
AMAZON_REGISTER_URL = "https://www.amazon.com/ap/register?openid.return_to=https%3A%2F%2Fdeveloper.amazon.com%2Fdashboard&openid.assoc_handle=mas_dev_portal&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"

async def pw_human_type(page, selector, text):
    """Playwright: ktiba b7al bashar - keyboard.press char b char"""
    try:
        el = page.locator(selector).first
        await el.evaluate("el => el.setAttribute('autocomplete', 'off')")
        await el.click()
        await page.wait_for_timeout(random.randint(100, 300))
        for char in text:
            await page.keyboard.type(char)
            await page.wait_for_timeout(random.randint(80, 200))
            if random.random() < 0.05:
                await page.wait_for_timeout(random.randint(200, 500))
        await page.keyboard.press("Tab")
    except Exception as e:
        pass

async def run_playwright_flow(app, prenom, nom, email, out_pass, dev_info=None):
    if dev_info is None:
        dev_info = {}
    from playwright.async_api import async_playwright
    full_name = f"{prenom} {nom}"
    app.update_status("Amazon Developer - Create Account (Playwright)...", "orange")
    app.log("1. Launching Chrome (Playwright)...")
    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(headless=False, channel="chrome")
    except Exception:
        browser = await p.chromium.launch(headless=False)
    app._current_browser = browser
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    try:
            app.log("2. Warmup Google...")
            await page.goto("https://www.google.com", wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(2500, 4500))

            app.log("3. Direct amazon.com/ap/register (bla dev portal)...")
            await page.goto(AMAZON_REGISTER_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(2500, 4000))

            email_only = await page.query_selector_all("#ap_email")
            name_fields = await page.query_selector_all("#ap_customer_name")
            if email_only and not name_fields:
                app.log("   Email-first flow...")
                await pw_human_type(page, "#ap_email", email)
                await page.wait_for_timeout(1000)
                try:
                    await page.click("#continue")
                except Exception:
                    pass
                await page.wait_for_timeout(random.randint(2500, 4000))

            app.log("4. Filling form (keyboard b7al human)...")
            if await page.query_selector("#ap_customer_name"):
                await pw_human_type(page, "#ap_customer_name", full_name)
                await page.wait_for_timeout(random.randint(600, 1200))
            if await page.query_selector("#ap_email"):
                val = await page.input_value("#ap_email")
                if not val:
                    await pw_human_type(page, "#ap_email", email)
                    await page.wait_for_timeout(random.randint(600, 1200))
            if await page.query_selector("#ap_password"):
                await pw_human_type(page, "#ap_password", out_pass)
                await page.wait_for_timeout(random.randint(600, 1200))
                if await page.query_selector("#ap_password_check"):
                    await pw_human_type(page, "#ap_password_check", out_pass)
                await page.wait_for_timeout(random.randint(800, 1500))

            app.log("5. Submitting form...")
            if await page.query_selector("#continue"):
                await page.click("#continue")
            await page.wait_for_timeout(2000)

            # Check if email already exists — match EXACT Amazon error messages only
            page_text_after = await page.inner_text("body") if await page.query_selector("body") else ""
            page_text_lower = page_text_after.lower()
            already_exists = (
                "there's already an account with this email" in page_text_lower or
                "already an account" in page_text_lower or
                "an account with this email address already exists" in page_text_lower or
                "already been taken" in page_text_lower or
                ("already exists" in page_text_lower and "sign in" in page_text_lower)
            )
            if already_exists:
                app.log(f"Email {email} deja kayn! SKIP...")
                app.update_status("Email already exists - SKIP", "red")
                app._last_result = "SKIP_EXISTS"
                return

            # Dismiss passkey/Windows Security dialog auto (press Escape)
            def _dismiss_passkey_loop():
                import ctypes
                for _ in range(15):
                    time.sleep(1)
                    try:
                        hwnd = ctypes.windll.user32.FindWindowW(None, "Sécurité Windows")
                        if not hwnd:
                            hwnd = ctypes.windll.user32.FindWindowW(None, "Windows Security")
                        if hwnd:
                            ctypes.windll.user32.PostMessageW(hwnd, 0x0100, 0x1B, 0)
                            app.log("   Passkey dialog dismissed (Escape).")
                    except Exception:
                        pass
            threading.Thread(target=_dismiss_passkey_loop, daemon=True).start()
            await page.wait_for_timeout(3000)

            app.log("Waiting for Amazon OTP (ou CAPTCHA)...")
            otp_selectors = ["#idTxtBx_SAOTCC_OTC", "#cvf_input_code", "#cvf-input-code", "#cvf-a-input-code", "input[name='otc']", "input[name='claimCode']", "input[autocomplete='one-time-code']", "input[placeholder*='code']", "input[placeholder*='security']", "input[maxlength='6']"]
            otp_found = None
            otp_sel = None
            phone_retries = 0
            for loop in range(50):
                if app._stop_flag:
                    app.log("STOPPED by user.")
                    return

                # CHECK OTP FIELD FIRST — before any skip logic!
                for sel in otp_selectors:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible():
                            otp_found = el
                            otp_sel = sel
                            break
                    except Exception:
                        pass
                if otp_found:
                    app.log("OTP input mawjoud! (Verify email) - ghadi nft7 Outlook...")
                    break

                page_url_lower = page.url.lower()
                on_otp_page = ("cvf" in page_url_lower or "/ap/mfa" in page_url_lower or
                               ("verify" in page_url_lower and "email" in page_url_lower))

                if not on_otp_page and loop >= 5:
                    visible_text = await page.inner_text("body") if await page.query_selector("body") else ""
                    visible_lower = visible_text.lower()

                    # Double-check: if page mentions OTP/code, treat as OTP page
                    if ("verification code" in visible_lower or
                        "one time password" in visible_lower or
                        "enter the code" in visible_lower or
                        "we sent" in visible_lower and "code" in visible_lower):
                        app.log(f"  Loop {loop}: OTP text detected, skipping identity/phone check...")
                        await page.wait_for_timeout(1000)
                        continue

                    # Identity verification → SKIP
                    if ("verify your identity" in visible_lower or
                        "identity verification" in visible_lower or
                        ("upload" in visible_lower and "photo" in visible_lower and "id" in visible_lower)):
                        app.log("VERIFICATION ID tlab! SKIP had l account...")
                        app.update_status("Verification ID - SKIP", "red")
                        app._last_result = "SKIP_VERIFICATION"
                        return

                    # Phone verification → retry or SKIP
                    if ("verify your phone" in visible_lower or
                        "add mobile number" in visible_lower or
                        "add your mobile phone number" in visible_lower or
                        ("phone" in page_url_lower and "verify" in page_url_lower)):
                        phone_indicators = await page.query_selector_all("input[type='tel']")
                        page_has_otp = any("code" in (await p.get_attribute("name") or "").lower() for p in phone_indicators) if phone_indicators else False
                        if phone_indicators and not page_has_otp:
                            phone_retries += 1
                            if phone_retries > 2:
                                app.log(f"Phone tlab {phone_retries} mrat! SKIP had l account.")
                                app.update_status("Phone asked 3x - SKIP", "red")
                                app._last_result = "SKIP_VERIFICATION"
                                return
                            app.log(f"Amazon tlab phone number! Retry {phone_retries}/2...")
                            app.update_status("Phone asked - New account...", "orange")
                        await context.clear_cookies()
                        await page.wait_for_timeout(500)
                        create_url = "https://www.amazon.com/ap/register?openid.return_to=https%3A%2F%2Fdeveloper.amazon.com%2Fdashboard&openid.assoc_handle=mas_dev_portal&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
                        await page.goto(create_url, wait_until="domcontentloaded")
                        await page.wait_for_timeout(3000)
                        create_link = await page.query_selector("a[id='createAccountSubmit']") or await page.query_selector("a:has-text('Create your Amazon account')") or await page.query_selector("a:has-text('Create account')")
                        if create_link:
                            app.log("   Clicking 'Create account' link...")
                            await create_link.click()
                            await page.wait_for_timeout(3000)
                        app.log("Re-filling registration form...")
                        if await page.query_selector("#ap_customer_name"):
                            await pw_human_type(page, "#ap_customer_name", full_name)
                        if await page.query_selector("#ap_email"):
                            await pw_human_type(page, "#ap_email", email)
                        if await page.query_selector("#ap_password"):
                            await pw_human_type(page, "#ap_password", out_pass)
                            if await page.query_selector("#ap_password_check"):
                                await pw_human_type(page, "#ap_password_check", out_pass)
                        if await page.query_selector("#continue"):
                            await page.click("#continue")
                        await page.wait_for_timeout(3000)
                        continue

                if "cvf" in page.url.lower():
                    app.log("CAPTCHA mawjoud (bla OTP field)! Siftiha b l'id, zed OK melli tkoun sali.")
                    app._wait_captcha_solved()
                    await page.wait_for_timeout(2000)
                    continue
                await page.wait_for_timeout(1000)

            if not otp_found:
                app.log("No OTP - logged in!")
                app.update_status("DONE - No OTP needed", "green")
                app.root.after(0, lambda: messagebox.showinfo("Najah!", "Dkhelna! Ma tlabach OTP."))
                return

            app.log("OTP requested! Tab 2 = Outlook...")
            otp = None
            try:
                page_outlook = await context.new_page()
                app.log("1. Dkhl Outlook - login.live.com...")
                await page_outlook.goto("https://login.live.com/", wait_until="domcontentloaded", timeout=30000)
                # EMAIL - selectors jdad (Microsoft bdlat #i0116 -> #usernameEntry)
                email_input = page_outlook.locator("#usernameEntry, #i0116, input[type='email'], input[name='loginfmt']").first
                await email_input.wait_for(state="visible", timeout=10000)
                await email_input.click()
                await page_outlook.wait_for_timeout(200)
                await page_outlook.keyboard.type(email, delay=80)
                app.log(f"   Email ktebna: {email}")
                await page_outlook.wait_for_timeout(400)
                # Click "Suivant" - selectors jdad
                suivant = page_outlook.locator("#idSIButton9, input[type='submit'], button[type='submit']").first
                await suivant.wait_for(state="visible", timeout=8000)
                await suivant.click()
                app.log("   Klikina Suivant.")
                await page_outlook.wait_for_timeout(4000)

                # PASSWORD - selectors jdad
                pw_input = page_outlook.locator("#i0118, input[type='password'], input[name='passwd']").first
                await pw_input.wait_for(state="visible", timeout=12000)
                await pw_input.click()
                await page_outlook.wait_for_timeout(200)
                await page_outlook.keyboard.type(out_pass, delay=80)
                app.log("   Password ktebna.")
                await page_outlook.wait_for_timeout(400)
                # Click "Se connecter"
                suivant2 = page_outlook.locator("#idSIButton9, input[type='submit'], button[type='submit']").first
                await suivant2.wait_for(state="visible", timeout=8000)
                try:
                    await suivant2.click(timeout=8000, no_wait_after=True)
                except Exception:
                    pass
                app.log("   Klikina Se connecter.")
                await page_outlook.wait_for_timeout(8000)

                # "Stay signed in?" - la
                try:
                    await page_outlook.locator("#idBtn_Back").click(timeout=3000)
                    await page_outlook.wait_for_timeout(2000)
                except Exception:
                    pass

                # Dismiss any passkey/interrupt page - loop
                for _ in range(5):
                    await page_outlook.wait_for_timeout(2000)
                    if "passkey" in page_outlook.url or "interrupt" in page_outlook.url:
                        app.log(f"   Passkey/interrupt page - click Annuler... ({page_outlook.url[:60]})")
                        dismissed = False
                        for sel in ["button:has-text('Annuler')", "button:has-text('Cancel')", "button:has-text('Skip')", "a:has-text('Annuler')", "button:has-text('Not now')"]:
                            try:
                                el = page_outlook.locator(sel).first
                                if await el.is_visible():
                                    await el.click()
                                    dismissed = True
                                    app.log("   Dismissed.")
                                    await page_outlook.wait_for_timeout(2000)
                                    break
                            except Exception:
                                continue
                        if not dismissed:
                            break
                    else:
                        break

                app.log("2. Naviqu l-inbox...")
                await page_outlook.goto("https://outlook.live.com/mail/0/inbox", wait_until="domcontentloaded", timeout=40000)
                await page_outlook.wait_for_timeout(5000)
                app.log(f"   URL daba: {page_outlook.url}")
                # Kan mazal f login page, nstana redirect
                if "login" in page_outlook.url or "live.com/login" in page_outlook.url:
                    app.log("   Mazal f login - kanstana redirect...")
                    await page_outlook.wait_for_timeout(10000)
                    app.log(f"   URL ba3d wait: {page_outlook.url}")
                # Kanstana 7ta search bar yban (inbox loaded)
                app.log("   Kanstana inbox yt7at...")
                for search_sel in ["#topSearchInput", "input[aria-label*='Search']", "input[placeholder*='Search']", "input[placeholder*='Rechercher']", "div[role='main']"]:
                    try:
                        await page_outlook.locator(search_sel).first.wait_for(state="visible", timeout=20000)
                        app.log(f"   Inbox loaded: {search_sel}")
                        break
                    except Exception:
                        continue
                await page_outlook.wait_for_timeout(3000)

                # Dismiss "newest Outlook" popup (No, thanks)
                try:
                    no_thanks = page_outlook.locator("button:has-text('No, thanks'), button:has-text('No thanks')").first
                    if await no_thanks.is_visible():
                        await no_thanks.click()
                        app.log("   Outlook popup dismissed (No, thanks)")
                        await page_outlook.wait_for_timeout(2000)
                except Exception:
                    pass

                app.log("   Dkhlna Outlook - inbox mafat7!")
                try:
                    await page_outlook.screenshot(path=os.path.join(BASE_DIR, "outlook_inbox.png"))
                except Exception:
                    pass
                app.log("3. Kanb7aw 3la email Amazon (search)...")
                # Search f inbox
                for sel in ["#topSearchInput", "input[aria-label*='Search']", "input[placeholder*='Search']", "input[placeholder*='Rechercher']"]:
                    try:
                        s = page_outlook.locator(sel).first
                        if await s.is_visible():
                            await s.click()
                            await page_outlook.wait_for_timeout(500)
                            await page_outlook.keyboard.type("Amazon", delay=80)
                            await page_outlook.keyboard.press("Enter")
                            app.log("   Search 'Amazon' done.")
                            break
                    except Exception:
                        continue
                await page_outlook.wait_for_timeout(6000)

                # Click 3la l-email dyal Amazon
                amazon_clicked = False
                for sel in ["[aria-label*='Amazon'], [aria-label*='Verify your new Amazon']",
                            "div[role='listitem']", "div[role='option']", "[data-convid]"]:
                    try:
                        rows = await page_outlook.query_selector_all(sel)
                        for row in rows[:10]:
                            txt = await row.text_content()
                            if txt and ("amazon" in txt.lower() or "verify" in txt.lower()):
                                await row.click()
                                app.log(f"   Klikina: {txt[:50].strip()}")
                                amazon_clicked = True
                                await page_outlook.wait_for_timeout(5000)
                                break
                        if amazon_clicked:
                            break
                    except Exception:
                        continue

                await page_outlook.wait_for_timeout(3000)

                # OTP: nakhdo HTML dyal l-page ba3d ma fta7na email (b7al backup)
                msg_body = await page_outlook.content()
                app.log("   Qrina HTML dyal page (b7al backup)")

                # Nawwlan: l9 OTP 9dam "One Time Password" wla "security code" context
                otp_context = re.search(r'(?:One Time Password|security code|OTP)[^\d]{0,100}(\d{6})', msg_body, re.IGNORECASE | re.DOTALL)
                if otp_context:
                    otp_matches = [otp_context.group(1)]
                    app.log(f"   OTP mn context: {otp_matches[0]}")
                else:
                    # Strip CSS colors (#rrggbb) 9bal regex
                    clean_body = re.sub(r'#[0-9a-fA-F]{6}', '', msg_body)
                    otp_matches = re.findall(r"\b\d{6}\b", clean_body)
                    if not otp_matches:
                        otp_matches = re.findall(r"\b\d{4,8}\b", clean_body)
                if not otp_matches:
                    app.log("   Mal9inach OTP automatic - ktebha b l'id...")
                    otp_event = threading.Event()
                    otp_manual = [None]
                    def _ask_otp():
                        val = tk.simpledialog.askstring("OTP Manual", "Mal9inach OTP automatic.\nKteb OTP b l'id (6 ar9am):")
                        otp_manual[0] = val
                        otp_event.set()
                    app.root.after(0, _ask_otp)
                    otp_event.wait(timeout=120)
                    if not otp_manual[0]:
                        raise Exception("OTP ma dakhalch.")
                    otp_matches = [otp_manual[0].strip()]
                otp = otp_matches[0]
                app.log(f"4. Khdina 6 ar9am mn l-message: {otp}")
                with open(os.path.join(BASE_DIR, "otp.txt"), "w") as f:
                    f.write(otp)
            except Exception as outlook_err:
                import traceback
                app.log(f"OUTLOOK ERROR: {outlook_err}")
                app.log(traceback.format_exc()[:500])
                # If OTP not found via Outlook, ask manually
                if not otp:
                    app.log("Outlook ma khdamch - kteb OTP b l'id...")
                    otp_event = threading.Event()
                    otp_manual = [None]
                    def _ask_otp_fallback():
                        val = tk.simpledialog.askstring("OTP Manual", "Outlook ma khdamch.\nKteb OTP b l'id (6 ar9am):")
                        otp_manual[0] = val
                        otp_event.set()
                    app.root.after(0, _ask_otp_fallback)
                    otp_event.wait(timeout=120)
                    if otp_manual[0]:
                        otp = otp_manual[0].strip()
                    else:
                        app.log("OTP ma dakhalch - SKIP")
                        app._last_result = "SKIP_VERIFICATION"

            # Paste OTP into Amazon if we have it
            if otp and otp_found and otp_sel:
                app.log("Retour Amazon - pasting OTP...")
                await page.bring_to_front()
                await page.wait_for_timeout(2000)

                await otp_found.fill("")
                await pw_human_type(page, otp_sel, otp)
                await page.wait_for_timeout(500)
                clicked = False
                for btn_sel in [
                    "#cvf-input-code-btn",
                    "input[value='Verify']",
                    "button:has-text('Verify')",
                    "button[type='submit']",
                    "input[type='submit']",
                    "#idSubmit_SAOTCC_Continue",
                    "#idSIButton9",
                    "#auth-verify-button",
                ]:
                    try:
                        await page.click(btn_sel, timeout=3000)
                        clicked = True
                        app.log(f"   Clicked: {btn_sel}")
                        break
                    except Exception:
                        continue
                if not clicked:
                    await page.keyboard.press("Enter")
                app.log("OTP pasted!")
                await page.wait_for_timeout(6000)

                # Developer Console Registration
                if dev_info.get("address") or dev_info.get("phone") or dev_info.get("city"):
                    app.log("Developer Console - Navigu l registration...")
                    app.update_status("Developer Console...", "orange")
                    await page.goto("https://developer.amazon.com/settings/console/registration", wait_until="domcontentloaded", timeout=40000)
                    await page.wait_for_timeout(4000)
                    app.log(f"   URL: {page.url}")

                    # Kan kayn login page, ndkhlou b nafs email + password
                    if "login" in page.url or "signin" in page.url or "ap/signin" in page.url:
                        app.log("   Developer portal - login, kanlogin...")
                        for sel in ["#ap_email", "input[type='email']", "input[name='email']", "input[placeholder*='téléphone']", "input[placeholder*='mail']"]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible():
                                    await el.click()
                                    await page.keyboard.type(email, delay=80)
                                    break
                            except Exception:
                                continue
                        await page.wait_for_timeout(400)
                        for sel in ["#continue", "input[type='submit']", "button:has-text('Continuer')", "button:has-text('Continue')"]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible():
                                    await el.click(no_wait_after=True)
                                    break
                            except Exception:
                                continue
                        await page.wait_for_timeout(3000)
                        for sel in ["#ap_password", "input[type='password']"]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible():
                                    await el.click()
                                    await page.keyboard.type(out_pass, delay=80)
                                    break
                            except Exception:
                                continue
                        await page.wait_for_timeout(400)
                        for sel in ["#signInSubmit", "input[type='submit']", "button[type='submit']"]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible():
                                    await el.click(no_wait_after=True)
                                    break
                            except Exception:
                                continue
                        await page.wait_for_timeout(6000)
                        app.log(f"   Login done. URL: {page.url}")

                    try:
                        await page.screenshot(path=os.path.join(BASE_DIR, "dev_console.png"))
                    except Exception:
                        pass

                    full_name = f"{prenom} {nom}"
                    business = dev_info.get("business") or full_name
                    country = dev_info.get("country", "United States")
                    address = dev_info.get("address", "")
                    city = dev_info.get("city", "")
                    zip_code = dev_info.get("zip", "")
                    state = dev_info.get("state", "")
                    phone_cc = dev_info.get("phone_cc", "+1")
                    phone = dev_info.get("phone", "")
                    support_email = email

                    async def fill_by_label(label_text, value):
                        """Find input by label text and fill it"""
                        if not value:
                            return False
                        try:
                            # label:has-text() + adjacent input wla sibling
                            for sel in [
                                f"label:has-text('{label_text}') + input",
                                f"label:has-text('{label_text}') ~ input",
                                f"label:has-text('{label_text}') + div input",
                                f"label:has-text('{label_text}') ~ div input",
                            ]:
                                try:
                                    el = page.locator(sel).first
                                    await el.scroll_into_view_if_needed()
                                    await page.wait_for_timeout(200)
                                    if await el.is_visible():
                                        await el.triple_click()
                                        await page.keyboard.type(value, delay=60)
                                        app.log(f"   '{label_text}': {value[:25]}")
                                        return True
                                except Exception:
                                    continue
                        except Exception:
                            pass
                        return False

                    try:
                        await page.screenshot(path=os.path.join(BASE_DIR, "dev_console.png"))
                    except Exception:
                        pass

                    # Wait for form to fully load
                    await page.wait_for_timeout(3000)

                    # COUNTRY (custom React dropdown)
                    try:
                        # Find the country input (placeholder "- Select -" or inside #country_code)
                        ci = None
                        for sel in ["#country_code input", "input[placeholder='- Select -']"]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible():
                                    ci = el
                                    break
                            except Exception:
                                continue
                        if ci:
                            await ci.scroll_into_view_if_needed()
                            await ci.click()
                            await page.wait_for_timeout(500)
                            await page.keyboard.type(country, delay=50)
                            await page.wait_for_timeout(1500)
                            # Click the option with mousedown
                            country_codes = {"United States": "US", "United Kingdom": "GB", "Germany": "DE",
                                           "France": "FR", "Netherlands": "NL", "Canada": "CA",
                                           "Australia": "AU", "Japan": "JP", "Spain": "ES",
                                           "Italy": "IT", "Brazil": "BR", "India": "IN",
                                           "Singapore": "SG", "Sweden": "SE", "Switzerland": "CH",
                                           "Belgium": "BE", "Poland": "PL", "Turkey": "TR"}
                            cc = country_codes.get(country, "")
                            # Try with value attribute first (more specific)
                            clicked = False
                            if cc:
                                try:
                                    await page.locator(f"div[value='{cc}'][title='{country}']").first.dispatch_event("mousedown")
                                    clicked = True
                                except Exception:
                                    pass
                            if not clicked:
                                await page.locator(f"div[title='{country}']").first.dispatch_event("mousedown")
                            app.log(f"   Country: {country}")
                            await page.wait_for_timeout(1000)
                    except Exception:
                        pass

                    # BUSINESS NAME (id='company_name')
                    try:
                        await page.locator("#company_name").click()
                        await page.wait_for_timeout(200)
                        await page.keyboard.type(business, delay=60)
                        app.log(f"   Business: {business}")
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)

                    # ADDRESS LINE 1 (id='address_line')
                    try:
                        await page.locator("#address_line").click()
                        await page.wait_for_timeout(200)
                        await page.keyboard.type(address, delay=60)
                        app.log(f"   Address: {address}")
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)

                    # CITY (id='city')
                    try:
                        await page.locator("#city").click()
                        await page.wait_for_timeout(200)
                        await page.keyboard.type(city, delay=60)
                        app.log(f"   City: {city}")
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)

                    # POSTAL CODE (id='postal_code')
                    try:
                        await page.locator("#postal_code").click()
                        await page.wait_for_timeout(200)
                        await page.keyboard.type(zip_code, delay=60)
                        app.log(f"   Postal: {zip_code}")
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)

                    # STATE (dropdown only for US, text input for others)
                    if state:
                        try:
                            si = page.locator("#state").first
                            await si.scroll_into_view_if_needed()
                            await si.click()
                            await page.wait_for_timeout(300)
                            await page.keyboard.type(state, delay=50)
                            # Only try dropdown for United States
                            if country == "United States":
                                await page.wait_for_timeout(1000)
                                try:
                                    await page.locator(f"div[title='{state}']").first.dispatch_event("mousedown")
                                except Exception:
                                    pass
                            app.log(f"   [OK] State: {state}")
                        except Exception:
                            pass
                    await page.wait_for_timeout(300)

                    # SAME AS PRIMARY EMAIL (id='ckbx_company_sup_email')
                    try:
                        cb = page.locator("#ckbx_company_sup_email")
                        await cb.scroll_into_view_if_needed()
                        await cb.evaluate("el => el.click()")
                        app.log("   Support email: Same as primary (checked)")
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)

                    # PHONE CC (custom React dropdown, placeholder='- CC -')
                    try:
                        cc_input = page.locator("input[placeholder='- CC -']").first
                        await cc_input.scroll_into_view_if_needed()
                        await cc_input.click()
                        await page.wait_for_timeout(800)
                        # Build CC label from country, e.g. "US (+1)"
                        cc_map = {"United States": "US (+1)", "United Kingdom": "GB (+44)", "Germany": "DE (+49)",
                                  "France": "FR (+33)", "Netherlands": "NL (+31)", "Canada": "CA (+1)",
                                  "Australia": "AU (+61)", "Japan": "JP (+81)", "Spain": "ES (+34)",
                                  "Italy": "IT (+39)", "Brazil": "BR (+55)", "India": "IN (+91)",
                                  "Singapore": "SG (+65)", "Sweden": "SE (+46)", "Switzerland": "CH (+41)",
                                  "Belgium": "BE (+32)", "Poland": "PL (+48)", "Turkey": "TR (+90)"}
                        cc_label = cc_map.get(country, "US (+1)")
                        cc_search = cc_label[:2].lower()
                        await page.keyboard.type(cc_search, delay=80)
                        await page.wait_for_timeout(1500)
                        await page.locator(f"div[title='{cc_label}']").first.dispatch_event("mousedown")
                        app.log(f"   Phone CC: {cc_label}")
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)

                    # PHONE NUMBER (id='company_phone')
                    if phone:
                        try:
                            await page.locator("#company_phone").click()
                            await page.wait_for_timeout(200)
                            await page.keyboard.type(phone, delay=60)
                            app.log(f"   Phone: {phone}")
                        except Exception:
                            pass
                    await page.wait_for_timeout(300)

                    # INTEREST: Developing apps (id='ckbx_registration_app_store_opt_in')
                    try:
                        cb = page.locator("#ckbx_registration_app_store_opt_in")
                        await cb.scroll_into_view_if_needed()
                        await cb.evaluate("el => el.click()")
                        app.log("   Interest: Developing apps checked")
                    except Exception:
                        pass
                    await page.wait_for_timeout(300)

                    # Click "Agree and Continue"
                    await page.wait_for_timeout(1000)
                    for sel in ["button:has-text('Agree and Continue')", "button:has-text('Save')", "button:has-text('Continue')", "button[type='submit']"]:
                        try:
                            el = page.locator(sel).first
                            if await el.is_visible():
                                await el.click()
                                app.log(f"   Clicked: {sel}")
                                break
                        except Exception:
                            continue
                    await page.wait_for_timeout(5000)
                    app.log(f"   Developer Console sali! URL: {page.url}")

                app.update_status(f"DONE! OTP {otp}", "green")
            elif not otp:
                app.log("OTP manl9awch - account SKIP")

    except Exception as e:
        import traceback
        if "TargetClosedError" in type(e).__name__ or "closed" in str(e).lower():
            app.log("Chrome tsad - normal.")
        else:
            app.log(f"Khata: {e}")
            app.log(traceback.format_exc()[:500])
    finally:
        # In batch mode: close browser cleanly and move on
        # In single mode: wait for user to close
        is_batch = getattr(app, '_batch_mode', False)
        try:
            if is_batch:
                app.log("Closing Chrome...")
                try:
                    await browser.close()
                except Exception:
                    pass
                try:
                    await p.stop()
                except Exception:
                    pass
                await asyncio.sleep(2)
            else:
                app.log("Chrome m7all - Siftu b l'id (X) melli t7ab.")
                if browser.is_connected():
                    while browser.is_connected():
                        await asyncio.sleep(1)
        except Exception:
            pass

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ProtonVPN + Amazon Developer + Outlook OTP")
        self.root.geometry("500x900")
        self.root.configure(padx=20, pady=15, bg="#f0f4f8")

        # Lwan: hmar #c0392b, khdar #27ae60, zra9 #3498db, sfar #f1c40f
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 9), background="#f0f4f8")
        style.configure("TLabelframe", background="#f0f4f8")
        style.configure("TLabelframe.Label", font=("Arial", 10, "bold"), foreground="#c0392b", background="#f0f4f8")

        ttk.Label(root, text="ProtonVPN → Amazon Developer → Outlook OTP", font=("Arial", 12, "bold"), foreground="#c0392b").pack(pady=5)

        # === 1. VPN (zra9) ===
        f_vpn = ttk.LabelFrame(root, text=" 1. Proton VPN (lawal) ", padding=8)
        f_vpn.pack(fill="x", pady=5)
        ttk.Label(f_vpn, text="Mode VPN:", foreground="#2980b9").grid(row=0, column=0, sticky="w", pady=2)
        self.vpn_mode = ttk.Combobox(f_vpn, width=32, state="readonly")
        self.vpn_mode['values'] = ("Auto (Proton VPN)", "Connect b l'id (Manual)")
        self.vpn_mode.current(0)
        self.vpn_mode.grid(row=0, column=1, pady=2, padx=5)
        ttk.Label(f_vpn, text="Dawla (Country):", foreground="#2980b9").grid(row=1, column=0, sticky="w", pady=2)
        self.vpn_country = ttk.Entry(f_vpn, width=37)
        self.vpn_country.insert(0, "United Kingdom")
        self.vpn_country.grid(row=1, column=1, pady=2, padx=5)

        # === 2. Amazon Developer - Create Account ===
        f_acc = ttk.LabelFrame(root, text=" 2. Amazon Developer - Create Account (3amar info) ", padding=8)
        f_acc.pack(fill="x", pady=5)
        ttk.Label(f_acc, text="Prenom:", foreground="#27ae60").grid(row=0, column=0, sticky="w", pady=2)
        self.prenom = ttk.Entry(f_acc, width=40)
        self.prenom.grid(row=0, column=1, pady=2, padx=5)
        ttk.Label(f_acc, text="Nom:", foreground="#27ae60").grid(row=1, column=0, sticky="w", pady=2)
        self.nom = ttk.Entry(f_acc, width=40)
        self.nom.grid(row=1, column=1, pady=2, padx=5)
        ttk.Label(f_acc, text="Email (Amazon = Outlook):", foreground="#27ae60").grid(row=2, column=0, sticky="w", pady=2)
        self.email = ttk.Entry(f_acc, width=40)
        self.email.grid(row=2, column=1, pady=2, padx=5)
        ttk.Label(f_acc, text="Password:", foreground="#27ae60").grid(row=3, column=0, sticky="w", pady=2)
        self.outlook_pass = ttk.Entry(f_acc, width=40, show="*")
        self.outlook_pass.grid(row=3, column=1, pady=2, padx=5)
        ttk.Label(f_acc, text="(OTP ywsel f Outlook - nakhdoha f nouvel onglet)", font=("Arial", 8), foreground="#666").grid(row=4, column=1, sticky="w")
        f_btns = tk.Frame(f_acc, bg="#f0f4f8")
        f_btns.grid(row=5, column=0, columnspan=2, pady=4)
        self.load_btn = tk.Button(f_btns, text="Load", command=self.load_profile, width=8, bg="#3498db", fg="white", cursor="hand2")
        self.load_btn.pack(side="left", padx=2)
        self.save_btn = tk.Button(f_btns, text="Save", command=self.save_profile, width=8, bg="#27ae60", fg="white", cursor="hand2")
        self.save_btn.pack(side="left", padx=2)

        # === 3. Developer Registration ===
        f_dev = ttk.LabelFrame(root, text=" 3. Amazon Developer Registration (3amar l-compte) ", padding=8)
        f_dev.pack(fill="x", pady=5)
        ttk.Label(f_dev, text="Business name:", foreground="#8e44ad").grid(row=0, column=0, sticky="w", pady=2)
        self.dev_business = ttk.Entry(f_dev, width=40)
        self.dev_business.grid(row=0, column=1, pady=2, padx=5)
        ttk.Label(f_dev, text="Country:", foreground="#8e44ad").grid(row=1, column=0, sticky="w", pady=2)
        self.dev_country = ttk.Combobox(f_dev, width=37, values=COUNTRIES)
        self.dev_country.set("United Kingdom")
        self.dev_country.grid(row=1, column=1, pady=2, padx=5)
        ttk.Label(f_dev, text="Address line 1:", foreground="#8e44ad").grid(row=2, column=0, sticky="w", pady=2)
        self.dev_address = ttk.Entry(f_dev, width=40)
        self.dev_address.grid(row=2, column=1, pady=2, padx=5)
        ttk.Label(f_dev, text="City:", foreground="#8e44ad").grid(row=3, column=0, sticky="w", pady=2)
        self.dev_city = ttk.Entry(f_dev, width=40)
        self.dev_city.grid(row=3, column=1, pady=2, padx=5)
        ttk.Label(f_dev, text="Postal code:", foreground="#8e44ad").grid(row=4, column=0, sticky="w", pady=2)
        self.dev_zip = ttk.Entry(f_dev, width=40)
        self.dev_zip.grid(row=4, column=1, pady=2, padx=5)
        ttk.Label(f_dev, text="State/Province:", foreground="#8e44ad").grid(row=5, column=0, sticky="w", pady=2)
        self.dev_state = ttk.Entry(f_dev, width=40)
        self.dev_state.grid(row=5, column=1, pady=2, padx=5)
        ttk.Label(f_dev, text="Phone CC (+1, +212...):", foreground="#8e44ad").grid(row=6, column=0, sticky="w", pady=2)
        self.dev_phone_cc = ttk.Entry(f_dev, width=10)
        self.dev_phone_cc.insert(0, "+1")
        self.dev_phone_cc.grid(row=6, column=1, pady=2, padx=5, sticky="w")
        ttk.Label(f_dev, text="Phone number:", foreground="#8e44ad").grid(row=7, column=0, sticky="w", pady=2)
        self.dev_phone = ttk.Entry(f_dev, width=40)
        self.dev_phone.grid(row=7, column=1, pady=2, padx=5)

        # === Batch CSV / Google Sheets ===
        f_batch = ttk.LabelFrame(root, text=" 4. Batch Mode (CSV / Google Sheets) ", padding=8)
        f_batch.pack(fill="x", pady=5)
        self.csv_path_var = tk.StringVar()
        ttk.Label(f_batch, text="Google Sheets URL\nou CSV File:", foreground="#e67e22").grid(row=0, column=0, sticky="w", pady=2)
        self.csv_entry = ttk.Entry(f_batch, width=30, textvariable=self.csv_path_var)
        self.csv_entry.grid(row=0, column=1, pady=2, padx=5)
        self.csv_browse_btn = tk.Button(f_batch, text="Browse", command=self._browse_csv, bg="#e67e22", fg="white", cursor="hand2")
        self.csv_browse_btn.grid(row=0, column=2, padx=3)
        self.sheets_refresh_btn = tk.Button(f_batch, text="Refresh", command=self._refresh_sheets, bg="#3498db", fg="white", cursor="hand2")
        self.sheets_refresh_btn.grid(row=1, column=2, padx=3)
        self.batch_progress_var = tk.StringVar(value="Paste Google Sheets published CSV link wla Browse CSV file")
        ttk.Label(f_batch, textvariable=self.batch_progress_var, foreground="#e67e22", font=("Arial", 8)).grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

        btn_frame = tk.Frame(root, bg="#f0f4f8")
        btn_frame.pack(pady=12)
        self.start_btn = tk.Button(btn_frame, text="▶ START", command=self.start_all,
                                   font=("Arial", 10, "bold"), bg="#27ae60", fg="white", activebackground="#2ecc71",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=15, pady=8)
        self.start_btn.pack(side="left", padx=5)
        self.batch_btn = tk.Button(btn_frame, text="▶ BATCH", command=self.start_batch,
                                   font=("Arial", 10, "bold"), bg="#e67e22", fg="white", activebackground="#d35400",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=15, pady=8)
        self.batch_btn.pack(side="left", padx=5)
        self.reset_btn = tk.Button(btn_frame, text="↺ RESET", command=self.reset_all,
                                   font=("Arial", 10, "bold"), bg="#e74c3c", fg="white", activebackground="#c0392b",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=15, pady=8)
        self.reset_btn.pack(side="left", padx=5)
        self._stop_flag = False
        self._batch_mode = False
        self._current_browser = None

        ttk.Label(root, text="Activity Log:", foreground="#f1c40f").pack(anchor="w")
        self.log_text = tk.Text(root, height=10, width=58, font=("Consolas", 8), state="disabled", bg="#fffde7", fg="#2c3e50", insertbackground="#c0392b")
        self.log_text.pack(pady=5)

        self.status_var = tk.StringVar()
        self.status_var.set("Wajed...")
        self.status_label = ttk.Label(root, textvariable=self.status_var, foreground="#3498db", font=("Arial", 9, "italic"))
        self.status_label.pack()

    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, f"[*] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")
        self.root.update()

    def update_status(self, text, color="blue"):
        self.status_var.set(text)
        self.status_label.configure(foreground=color)
        self.root.update()

    def load_profile(self):
        path = filedialog.askopenfilename(
            title="Load profile (EMAILNAME.txt)",
            initialdir=BASE_DIR,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            data = {"prenom": "", "nom": "", "email": "", "password": "", "business": "", "country": "", "address": "", "city": "", "zip": "", "state": "", "phone_cc": "+1", "phone": ""}
            for line in lines:
                up = line.upper()
                if up.startswith("PRENOM:"):
                    data["prenom"] = line.split(":", 1)[1].strip()
                elif up.startswith("NOM:"):
                    data["nom"] = line.split(":", 1)[1].strip()
                elif up.startswith("BUSINESS:"):
                    data["business"] = line.split(":", 1)[1].strip()
                elif up.startswith("COUNTRY:"):
                    data["country"] = line.split(":", 1)[1].strip()
                elif up.startswith("ADDRESS:"):
                    data["address"] = line.split(":", 1)[1].strip()
                elif up.startswith("CITY:"):
                    data["city"] = line.split(":", 1)[1].strip()
                elif up.startswith("ZIP:"):
                    data["zip"] = line.split(":", 1)[1].strip()
                elif up.startswith("STATE:"):
                    data["state"] = line.split(":", 1)[1].strip()
                elif up.startswith("PHONE_CC:"):
                    data["phone_cc"] = line.split(":", 1)[1].strip()
                elif up.startswith("PHONE:"):
                    data["phone"] = line.split(":", 1)[1].strip()
                elif "@" in line and "." in line and " " not in line and not data["email"]:
                    data["email"] = line
                elif (not data["password"] and len(line) >= 8
                      and not up.startswith("TARGET") and not up.startswith("NOM")
                      and not up.startswith("PRENOM") and line != data["email"]):
                    data["password"] = line
            self.prenom.delete(0, tk.END)
            self.prenom.insert(0, data["prenom"])
            self.nom.delete(0, tk.END)
            self.nom.insert(0, data["nom"])
            self.email.delete(0, tk.END)
            self.email.insert(0, data["email"])
            self.outlook_pass.delete(0, tk.END)
            self.outlook_pass.insert(0, data["password"])
            self.dev_business.delete(0, tk.END)
            self.dev_business.insert(0, data["business"])
            if data["country"]:
                self.dev_country.set(data["country"])
            self.dev_address.delete(0, tk.END)
            self.dev_address.insert(0, data["address"])
            self.dev_city.delete(0, tk.END)
            self.dev_city.insert(0, data["city"])
            self.dev_zip.delete(0, tk.END)
            self.dev_zip.insert(0, data["zip"])
            self.dev_state.delete(0, tk.END)
            self.dev_state.insert(0, data["state"])
            self.dev_phone_cc.delete(0, tk.END)
            self.dev_phone_cc.insert(0, data["phone_cc"])
            self.dev_phone.delete(0, tk.END)
            self.dev_phone.insert(0, data["phone"])
            self.log(f"Loaded: {path}")
        except Exception as e:
            messagebox.showerror("Load", str(e))

    def _check_vpn_ip(self):
        """Check current IP via API to verify VPN connection"""
        try:
            import urllib.request, json
            req = urllib.request.Request("https://ipinfo.io/json",
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return data.get("ip", "?"), data.get("country", "?"), data.get("org", "?")
        except Exception:
            return None, None, None

    def _focus_proton_window(self):
        """Bring Proton VPN window to front, return (hwnd, x, y, w, h) or None"""
        try:
            import ctypes
            import ctypes.wintypes
            import time as _t

            hwnd = ctypes.windll.user32.FindWindowW(None, "Proton VPN")
            if not hwnd:
                self.log("Proton VPN window mal9ach...")
                return None

            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            _t.sleep(0.5)

            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            return (hwnd, rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
        except Exception as e:
            self.log(f"Window error: {e}")
            return None

    def _click_proton_connect_country(self, country):
        """Search for country in Proton VPN and connect to it"""
        try:
            import pyautogui
            import time as _t

            info = self._focus_proton_window()
            if not info:
                return False
            hwnd, win_x, win_y, win_w, win_h = info
            self.log(f"Proton VPN window: {win_w}x{win_h} at ({win_x},{win_y})")

            # Sidebar is ~280px wide on left side
            sidebar_center_x = win_x + 140

            # Step 1: Click search bar "Browse from..." at top of sidebar (~69px from top)
            search_x = sidebar_center_x
            search_y = win_y + 69
            self.log(f"1. Click search bar...")
            pyautogui.click(search_x, search_y)
            _t.sleep(0.5)

            # Step 2: Clear any existing text and type country name
            pyautogui.hotkey('ctrl', 'a')
            _t.sleep(0.2)
            pyautogui.typewrite(country, interval=0.05)
            _t.sleep(1)
            self.log(f"2. Typed: {country}")

            # Step 3: Click "All" tab (first tab, leftmost)
            all_tab_x = win_x + 30
            all_tab_y = search_y + 45
            self.log(f"3. Clicking 'All' tab...")
            pyautogui.click(all_tab_x, all_tab_y)
            _t.sleep(1)

            # Step 4: Hover over the country entry to reveal the "Connect" button
            # Layout: All tab → "Country (1)" header (~35px) → country entry (~45px)
            country_y = all_tab_y + 155
            self.log(f"4. Hovering over country entry...")
            pyautogui.moveTo(sidebar_center_x, country_y)
            _t.sleep(0.8)

            # Step 5: Click the "Connect" button that appears on hover
            # "Connect" is at roughly 63% of sidebar width from left edge
            sidebar_w = min(win_w, 310)
            connect_btn_x = win_x + int(sidebar_w * 0.63)
            self.log(f"5. Clicking 'Connect' button at ({connect_btn_x}, {country_y})...")
            pyautogui.click(connect_btn_x, country_y)
            _t.sleep(2)

            self.log(f"Clicked connect for: {country}")
            return True
        except Exception as e:
            self.log(f"Auto-click error: {e}")
            return False

    def connect_vpn_proton(self):
        country = self.vpn_country.get().strip()
        if not country:
            country = "United States"
        mode = self.vpn_mode.get()

        # Get initial IP before VPN
        self.log("Kanchuf IP bla VPN...")
        orig_ip, orig_cc, _ = self._check_vpn_ip()
        if orig_ip:
            self.log(f"IP daba (bla VPN): {orig_ip} | Country: {orig_cc}")

        if "Manual" in mode:
            self.log(f"Connect Proton VPN to {country} b l'id daba...")
            messagebox.showinfo("VPN Manual",
                f"1. Ft7 Proton VPN\n2. Connect 3la {country}\n3. Tsana bach VPN ytconnecti (icon akhdar)\n4. Zed OK melli tkoun connecti")
        else:
            # Auto mode: launch Proton VPN and click Connect
            self.log("Proton VPN kayft7...")
            if not os.path.exists(PROTON_VPN_EXE):
                self.log("Proton VPN mal9ach! Install it wla sta3mel Manual mode.")
                messagebox.showwarning("VPN", "Proton VPN mal9ach!\nSta3mel Manual mode wla install Proton VPN.")
                return False
            try:
                subprocess.Popen([PROTON_VPN_EXE], shell=False)
                self.log("Proton VPN tft7at!")
            except Exception as e:
                self.log(f"VPN launch error: {e}")

            # Wait for Proton VPN window to appear
            self.log("Tsana Proton VPN window...")
            time.sleep(5)

            # Auto-search country and click connect
            self._click_proton_connect_country(country)

        # Poll until IP changes (VPN connected) — max 90 sec
        self.log("Kanchuf wach VPN connecti...")
        for i in range(18):
            new_ip, new_cc, new_org = self._check_vpn_ip()
            if new_ip and orig_ip and new_ip != orig_ip:
                self.log(f"VPN CONNECTI! IP: {new_ip} | Country: {new_cc} | {new_org}")
                time.sleep(3)
                return True
            if i == 6:
                # Try again after 30 sec in case first click missed
                self._click_proton_connect_country(country)
            self.log(f"  Tsana VPN... ({(i+1)*5}s)")
            time.sleep(5)

        # Timeout
        new_ip, new_cc, new_org = self._check_vpn_ip()
        if new_ip and orig_ip and new_ip != orig_ip:
            self.log(f"VPN CONNECTI! IP: {new_ip} | Country: {new_cc} | {new_org}")
            return True

        self.log("VPN ma connectatch! Connect b l'id w 3awed START.")
        return False

    def connect_vpn_proton_country(self, country):
        """Connect VPN to specific country (for batch mode)"""
        self.log(f"VPN → {country}...")

        # Get initial IP
        orig_ip, orig_cc, _ = self._check_vpn_ip()
        if orig_ip:
            self.log(f"IP daba: {orig_ip} | {orig_cc}")

        # Launch Proton VPN if not running
        info = self._focus_proton_window()
        if not info:
            if os.path.exists(PROTON_VPN_EXE):
                subprocess.Popen([PROTON_VPN_EXE], shell=False)
                self.log("Proton VPN kayft7...")
                time.sleep(5)

        # Search and connect to country
        self._click_proton_connect_country(country)

        # Poll until IP changes — max 60 sec
        self.log("Kanchuf wach VPN connecti...")
        for i in range(12):
            new_ip, new_cc, new_org = self._check_vpn_ip()
            if new_ip and orig_ip and new_ip != orig_ip:
                self.log(f"VPN CONNECTI! IP: {new_ip} | Country: {new_cc} | {new_org}")
                time.sleep(3)
                return True
            if i == 5:
                self._click_proton_connect_country(country)
            self.log(f"  Tsana VPN... ({(i+1)*5}s)")
            time.sleep(5)

        self.log(f"VPN {country} ma connectatch — kaymchi...")
        return False

    def save_profile(self):
        path = filedialog.asksaveasfilename(
            title="Save profile",
            initialdir=BASE_DIR,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"PRENOM: {self.prenom.get().strip()}\n")
                f.write(f"NOM: {self.nom.get().strip()}\n")
                f.write(f"{self.email.get().strip()}\n")
                f.write(f"{self.outlook_pass.get().strip()}\n")
                f.write(f"BUSINESS: {self.dev_business.get().strip()}\n")
                f.write(f"COUNTRY: {self.dev_country.get().strip()}\n")
                f.write(f"ADDRESS: {self.dev_address.get().strip()}\n")
                f.write(f"CITY: {self.dev_city.get().strip()}\n")
                f.write(f"ZIP: {self.dev_zip.get().strip()}\n")
                f.write(f"STATE: {self.dev_state.get().strip()}\n")
                f.write(f"PHONE_CC: {self.dev_phone_cc.get().strip()}\n")
                f.write(f"PHONE: {self.dev_phone.get().strip()}\n")
            self.log(f"Saved: {path}")
        except Exception as e:
            messagebox.showerror("Save", str(e))

    def reset_all(self):
        """Kill Chrome, re-enable START, clear log"""
        self._stop_flag = True
        # Kill Chrome
        try:
            if self._current_browser and self._current_browser.is_connected():
                import subprocess
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
        except Exception:
            import subprocess
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
        self.start_btn.configure(state="normal")
        self.batch_btn.configure(state="normal")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")
        self.update_status("Reset - Wajed bach t3awed.", "blue")
        self.log("Reset done. Ready to START again.")

    def start_all(self):
        prenom = self.prenom.get().strip()
        nom = self.nom.get().strip()
        email = self.email.get().strip()
        out_pass = self.outlook_pass.get().strip()
        if not prenom or not nom:
            messagebox.showerror("Erreur", "Dakhel Prenom w Nom.")
            return
        if not email or not out_pass:
            messagebox.showerror("Erreur", "Dakhel email w password.")
            return
        self._stop_flag = False
        self.start_btn.configure(state="disabled")
        self.update_status("Starting...", "orange")
        dev_info = {
            "business": self.dev_business.get().strip(),
            "country": self.dev_country.get().strip(),
            "address": self.dev_address.get().strip(),
            "city": self.dev_city.get().strip(),
            "zip": self.dev_zip.get().strip(),
            "state": self.dev_state.get().strip(),
            "phone_cc": self.dev_phone_cc.get().strip(),
            "phone": self.dev_phone.get().strip(),
        }
        thread = threading.Thread(target=self.run_full_flow, args=(prenom, nom, email, out_pass, dev_info))
        thread.daemon = True
        thread.start()

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.csv_path_var.set(path)
            self._load_csv_data()

    def _refresh_sheets(self):
        """Refresh data from Google Sheets or CSV"""
        self._load_csv_data()

    def _load_csv_data(self):
        """Load accounts from CSV file or Google Sheets URL"""
        source = self.csv_path_var.get().strip()
        if not source:
            messagebox.showerror("Erreur", "Dakhel Google Sheets URL wla CSV file path!")
            return []

        try:
            import csv, io
            if source.startswith("http"):
                # Google Sheets published CSV URL
                import urllib.request
                self.log(f"Loading from Google Sheets...")
                req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    content = resp.read().decode("utf-8")
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)
            else:
                # Local CSV file
                with open(source, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

            self.batch_rows = rows
            self.batch_progress_var.set(f"{len(rows)} accounts loaded!")
            self.log(f"Loaded: {len(rows)} accounts")
            return rows
        except Exception as e:
            messagebox.showerror("Error", f"Ma9dertch nqra l data:\n{e}")
            return []

    def start_batch(self):
        rows = self._load_csv_data()
        if not rows:
            return

        self._stop_flag = False
        self.start_btn.configure(state="disabled")
        self.batch_btn.configure(state="disabled")
        thread = threading.Thread(target=self._run_batch)
        thread.daemon = True
        thread.start()

    def _run_batch(self):
        self._batch_mode = True
        total = len(self.batch_rows)
        results = {"ok": [], "skip": [], "fail": []}
        for idx, row in enumerate(self.batch_rows):
            if self._stop_flag:
                self.log("BATCH STOPPED by user.")
                break

            self.log(f"\n{'='*40}")
            self.log(f"ACCOUNT {idx+1}/{total}")
            self.log(f"{'='*40}")
            self.root.after(0, lambda i=idx, t=total: self.batch_progress_var.set(f"Account {i+1}/{t}"))
            self.update_status(f"Batch: {idx+1}/{total} | OK:{len(results['ok'])} SKIP:{len(results['skip'])} FAIL:{len(results['fail'])}", "orange")

            # Read fields from CSV row
            prenom = row.get("prenom", row.get("first_name", "")).strip()
            nom = row.get("nom", row.get("last_name", "")).strip()
            email = row.get("email", "").strip()
            out_pass = row.get("password", row.get("pass", "")).strip()

            if not prenom or not nom or not email or not out_pass:
                self.log(f"SKIP: missing prenom/nom/email/password")
                continue

            dev_info = {
                "business": row.get("business", row.get("business_name", "")).strip(),
                "country": row.get("country", "United Kingdom").strip(),
                "address": row.get("address", row.get("address_line", "")).strip(),
                "city": row.get("city", "").strip(),
                "zip": row.get("zip", row.get("postal_code", "")).strip(),
                "state": row.get("state", row.get("province", "")).strip(),
                "phone_cc": row.get("phone_cc", "").strip(),
                "phone": row.get("phone", row.get("phone_number", "")).strip(),
            }

            # Set VPN country from CSV for this account
            account_country = dev_info["country"]
            self.log(f"Email: {email} | Name: {prenom} {nom} | Country: {account_country}")
            self.root.after(0, lambda c=account_country: (self.vpn_country.delete(0, tk.END), self.vpn_country.insert(0, c)))

            self._last_result = None
            try:
                # Connect VPN to account's country
                self.connect_vpn_proton_country(account_country)
                # Run the flow (skip VPN step since already connected)
                asyncio.run(run_playwright_flow(self, prenom, nom, email, out_pass, dev_info or {}))
                if self._last_result in ("SKIP_VERIFICATION", "SKIP_EXISTS"):
                    results["skip"].append(email)
                    reason = "Verification ID" if self._last_result == "SKIP_VERIFICATION" else "Email deja kayn"
                    self.log(f"SKIPPED: {email} ({reason})")
                else:
                    results["ok"].append(email)
                    self.log(f"OK: {email}")
            except Exception as e:
                if "TargetClosedError" in type(e).__name__ or "closed" in str(e).lower():
                    self.log("Chrome tsad - normal.")
                    results["skip"].append(email)
                else:
                    self.log(f"FAIL: {email} - {e}")
                    results["fail"].append(email)

            self.log(f"Account {idx+1}/{total} | OK:{len(results['ok'])} SKIP:{len(results['skip'])} FAIL:{len(results['fail'])}")

            # Small pause between accounts
            if idx < total - 1 and not self._stop_flag:
                self.log("Pause 10 sec before next account...")
                time.sleep(10)

        # Final summary
        self.log(f"\n{'='*40}")
        self.log(f"BATCH FINISHED!")
        self.log(f"  OK:   {len(results['ok'])} accounts")
        self.log(f"  SKIP: {len(results['skip'])} accounts")
        self.log(f"  FAIL: {len(results['fail'])} accounts")
        if results["ok"]:
            self.log(f"\nACCOUNTS OK:")
            for e in results["ok"]:
                self.log(f"  {e}")
        if results["skip"]:
            self.log(f"\nACCOUNTS SKIPPED:")
            for e in results["skip"]:
                self.log(f"  {e}")
        if results["fail"]:
            self.log(f"\nACCOUNTS FAILED:")
            for e in results["fail"]:
                self.log(f"  {e}")
        self.update_status(f"Done! OK:{len(results['ok'])} SKIP:{len(results['skip'])} FAIL:{len(results['fail'])}", "green")
        self.root.after(0, lambda: self.batch_progress_var.set(f"Done: OK:{len(results['ok'])} SKIP:{len(results['skip'])} FAIL:{len(results['fail'])}"))
        try:
            self.start_btn.configure(state="normal")
            self.batch_btn.configure(state="normal")
        except Exception:
            pass
        self._batch_mode = False
        self.root.after(0, lambda: self.start_btn.configure(state="normal"))
        self.root.after(0, lambda: self.batch_btn.configure(state="normal"))

    def _wait_captcha_solved(self):
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        captcha_done = threading.Event()
        def _show():
            messagebox.showinfo("CAPTCHA - Solve b l'id", "Solve the puzzle b l'id.\nMelli tsaliw w tzad Confirm, zed OK.\nGhadi nkamlou l Outlook.")
            captcha_done.set()
        self.root.after(0, _show)
        captcha_done.wait(timeout=180)
        self.root.attributes('-topmost', False)

    def run_full_flow(self, prenom, nom, email, out_pass, dev_info=None):
        try:
            self.connect_vpn_proton()
            asyncio.run(run_playwright_flow(self, prenom, nom, email, out_pass, dev_info or {}))
        except Exception as e:
            if "TargetClosedError" in type(e).__name__ or "closed" in str(e).lower():
                self.log("Chrome tsad - normal.")
            else:
                import traceback
                traceback.print_exc()
                self.log(f"ERROR: {str(e)}")
                self.update_status("Erreur!", "red")
        finally:
            self.log("Finished.")
            try:
                self.start_btn.configure(state="normal")
            except Exception:
                pass
            try:
                self.root.after(0, lambda: self.start_btn.configure(state="normal"))
            except Exception:
                pass
            self.log("Wajed bach t3awed START.")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
