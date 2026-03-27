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
import ctypes

if sys.platform == "win32":
    # Auto-elevate to admin for WireGuard (UAC mra wa7da bss)
    def _is_admin():
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    if not _is_admin():
        script = os.path.abspath(__file__)
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}"', None, 1)
        sys.exit(0)
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

COUNTRIES = [
    "United Kingdom", "Germany", "France", "Netherlands",
    "Canada", "Australia", "Japan", "Spain", "Italy", "Brazil", "India",
    "Singapore", "Sweden", "Switzerland", "Belgium", "Poland", "Turkey",
    "Denmark", "Finland"
]

# Map country names to WireGuard config country codes
COUNTRY_TO_CODE = {
    "United Kingdom": "UK", "Germany": "DE", "France": "FR", "Netherlands": "NL",
    "Canada": "CA", "Australia": "AU", "Japan": "JP", "Spain": "ES", "Italy": "IT",
    "Brazil": "BR", "India": "IN", "Singapore": "SG", "Sweden": "SE",
    "Switzerland": "CH", "Belgium": "BE", "Poland": "PL", "Turkey": "TR",
    "Denmark": "DK", "Finland": "FI", "United States": "US",
    "Croatia": "HR", "Luxembourg": "LU", "Portugal": "PT",
    "Austria": "AT", "Greece": "GR",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VPN_CONFIGS_DIR = os.path.join(BASE_DIR, "vpn_configs")
WIREGUARD_EXE = r"C:\Program Files\WireGuard\wireguard.exe"
WG_EXE = r"C:\Program Files\WireGuard\wg.exe"
LOG_FILE = os.path.join(BASE_DIR, "debug.log")

def flog(msg):
    """Write to debug log file"""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass
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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]

async def run_playwright_flow(app, prenom, nom, email, out_pass, dev_info=None):
    if dev_info is None:
        dev_info = {}
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    full_name = f"{prenom} {nom}"
    app.update_status("Amazon Developer - Create Account (Playwright)...", "orange")
    app.log("1. Launching Chrome (Playwright + Stealth)...")
    p = await async_playwright().start()
    try:
        browser = await p.chromium.launch(headless=False, channel="chrome")
    except Exception:
        browser = await p.chromium.launch(headless=False)
    app._current_browser = browser
    # Store PID so we only kill THIS chrome, not user's chrome
    try:
        app._browser_pid = browser.process.pid
        flog(f"Browser PID: {app._browser_pid}")
    except Exception:
        app._browser_pid = None
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

            # If redirected to signin page, click "Create your Amazon Developer account"
            if "signin" in page.url.lower() and "register" not in page.url.lower():
                app.log("   Redirected to Sign In → clicking Create...")
                for create_sel in [
                    "a:has-text('Create your Amazon Developer account')",
                    "a[id='createAccountSubmit']",
                    "#auth-create-account-link",
                    "a:has-text('Create your Amazon account')",
                    "a:has-text('Create account')",
                ]:
                    try:
                        el = page.locator(create_sel).first
                        if await el.is_visible():
                            await el.click()
                            app.log(f"   Clicked: {create_sel}")
                            await page.wait_for_timeout(3000)
                            break
                    except Exception:
                        continue

            # Detect email-first sign-in (old #ap_email OR new placeholder-based input)
            email_only = await page.query_selector("#ap_email")
            email_init_sel = "#ap_email" if email_only else None
            if not email_only:
                for sel in ["input[type='email']", "input[placeholder*='email']", "input[placeholder*='mobile']"]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible():
                            email_init_sel = sel
                            break
                    except Exception:
                        continue
            name_fields = await page.query_selector_all("#ap_customer_name")
            if email_init_sel and not name_fields:
                app.log(f"   Email-first flow ({email_init_sel})...")
                await pw_human_type(page, email_init_sel, email)
                await page.wait_for_timeout(1000)
                for btn in ["#continue", "input[type='submit']", "button:has-text('Continue')", "button:has-text('Sign in')"]:
                    try:
                        el = page.locator(btn).first
                        if await el.is_visible():
                            await el.click()
                            break
                    except Exception:
                        continue
                await page.wait_for_timeout(random.randint(2500, 4000))

                # CHECK "cannot find account" FIRST — before clicking Create
                try:
                    _post_continue_text = (await page.inner_text("body")).lower() if await page.query_selector("body") else ""
                except Exception:
                    _post_continue_text = ""
                if ("cannot find" in _post_continue_text or "can\u2019t find" in _post_continue_text or
                    "no account found" in _post_continue_text or
                    ("problem" in _post_continue_text and "cannot find" in _post_continue_text)):
                    app.log("'Cannot find account' after Continue → SKIP → next account.")
                    app.update_status("Cannot find account - SKIP", "orange")
                    app._last_result = "phone"
                    return

                # Try to click "Create your Amazon Developer account" after Continue
                app.log("   Looking for 'Create' button...")
                create_clicked = False
                for create_sel in [
                    "a:has-text('Create your Amazon Developer account')",
                    "button:has-text('Create your Amazon Developer account')",
                    "span:has-text('Create your Amazon Developer account')",
                    "a[id='createAccountSubmit']",
                    "#auth-create-account-link",
                    "a:has-text('Create your Amazon account')",
                    "a:has-text('Create a new Amazon account')",
                    "a:has-text('Create account')",
                    "button:has-text('Create account')",
                    "[data-action='sign-up']",
                ]:
                    try:
                        el = page.locator(create_sel).first
                        if await el.is_visible():
                            await el.click()
                            create_clicked = True
                            app.log(f"   Clicked: {create_sel}")
                            await page.wait_for_timeout(3000)
                            break
                    except Exception:
                        continue

                if not create_clicked:
                    app.log("   Create button mal9ach — continuing...")

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
            try:
                page_text_after = await page.inner_text("body") if await page.query_selector("body") else ""
            except Exception:
                await page.wait_for_timeout(2000)
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
            _stuck_url = ""
            _stuck_count = 0
            flog("=== OTP LOOP START ===")
            for loop in range(50):
                if app._stop_flag or getattr(app, '_skip_flag', False):
                    flog(f"Loop {loop}: STOP/SKIP flag set")
                    app.log("STOPPED/NEXT by user.")
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
                    flog(f"Loop {loop}: OTP FOUND via {otp_sel}")
                    app.log("OTP input mawjoud! (Verify email) - ghadi nft7 Outlook...")
                    break

                flog(f"Loop {loop}: no OTP, URL={page.url[:80]}")

                page_url_lower = page.url.lower()
                on_otp_page = ("cvf" in page_url_lower or "/ap/mfa" in page_url_lower or
                               ("verify" in page_url_lower and "email" in page_url_lower))

                # Phone verification → SKIP immediately (check every loop from loop 2+)
                if loop >= 2:
                    # Check URL first (fast)
                    if "phone" in page_url_lower and "verify" in page_url_lower:
                        app.log("Amazon tlab phone number! SKIP → next account.")
                        app.update_status("Phone asked - SKIP", "orange")
                        app._last_result = "phone"
                        return
                    # Check for phone input fields (tel type)
                    try:
                        phone_input = await page.query_selector("input[type='tel']")
                        if phone_input:
                            # Make sure it's not an OTP field
                            ph_name = (await phone_input.get_attribute("name") or "").lower()
                            ph_id = (await phone_input.get_attribute("id") or "").lower()
                            if "code" not in ph_name and "otp" not in ph_name and "code" not in ph_id and "otp" not in ph_id:
                                visible_text_ph = await page.inner_text("body") if await page.query_selector("body") else ""
                                visible_lower_ph = visible_text_ph.lower()
                                if ("phone" in visible_lower_ph or "mobile" in visible_lower_ph or
                                    "numéro" in visible_lower_ph or "telefon" in visible_lower_ph):
                                    app.log("Amazon tlab phone number! SKIP → next account.")
                                    app.update_status("Phone asked - SKIP", "orange")
                                    app._last_result = "phone"
                                    return
                    except Exception:
                        pass

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
                        flog(f"Loop {loop}: IDENTITY SKIP triggered! text={visible_lower[:200]}")
                        app.log("VERIFICATION ID tlab! SKIP had l account...")
                        app.update_status("Verification ID - SKIP", "red")
                        app._last_result = "SKIP_VERIFICATION"
                        return

                    # Phone verification (text-based fallback) → SKIP
                    if ("verify your phone" in visible_lower or
                        "add mobile number" in visible_lower or
                        "add your mobile phone number" in visible_lower or
                        "mobile phone number" in visible_lower or
                        "enter your mobile" in visible_lower or
                        "phone number" in visible_lower and "verify" in visible_lower):
                        app.log("Amazon tlab phone number! SKIP → next account.")
                        app.update_status("Phone asked - SKIP", "orange")
                        app._last_result = "phone"
                        return

                if "cvf" in page.url.lower():
                    # Check if it's a CAPTCHA page — only real captcha elements
                    is_captcha = False
                    try:
                        captcha_el = await page.query_selector("#captchacharacters, #auth-captcha-image, img[src*='captcha'], iframe[title*='challenge'], input[name='cvf_captcha_captcha_token']")
                        if captcha_el:
                            is_captcha = True
                    except Exception:
                        pass
                    # Also check page text for captcha keywords
                    if not is_captcha and loop >= 8:
                        try:
                            cvf_text = (await page.inner_text("body")).lower() if await page.query_selector("body") else ""
                            if "captcha" in cvf_text or "puzzle" in cvf_text or "type the characters" in cvf_text:
                                is_captcha = True
                        except Exception:
                            pass
                    # Last resort: 15 loops (15 sec) on CVF with no OTP = probably captcha
                    if not is_captcha and loop >= 15:
                        is_captcha = True
                    if is_captcha:
                        app.log("CAPTCHA detected! SKIP had l account.")
                        app.update_status("CAPTCHA - SKIP", "red")
                        app._last_result = "SKIP_CAPTCHA"
                        return

                # === "CANNOT FIND ACCOUNT" on sign-in → SKIP immediately ===
                cur_url = page.url
                if "signin" in cur_url.lower() or "sign-in" in cur_url.lower() or "ap/signin" in cur_url.lower():
                    try:
                        _signin_text = (await page.inner_text("body")).lower() if await page.query_selector("body") else ""
                        if ("cannot find" in _signin_text or "can\u2019t find" in _signin_text or
                            "no account found" in _signin_text or
                            ("problem" in _signin_text and "email" in _signin_text and "cannot" in _signin_text)):
                            app.log("'Cannot find account' on sign-in → SKIP → next account.")
                            app.update_status("Cannot find account - SKIP", "orange")
                            app._last_result = "phone"
                            return
                    except Exception:
                        pass

                # === STUCK DETECTION: analyze page and take action ===
                if cur_url == _stuck_url:
                    _stuck_count += 1
                else:
                    _stuck_url = cur_url
                    _stuck_count = 0

                if _stuck_count >= 5:
                    app.log(f"   STUCK detected ({_stuck_count} loops on same URL)! Analyzing...")
                    try:
                        stuck_text = (await page.inner_text("body")).lower() if await page.query_selector("body") else ""
                    except Exception:
                        stuck_text = ""
                    stuck_url_lower = cur_url.lower()

                    # On sign-in page → check if "cannot find account" = SKIP
                    if "signin" in stuck_url_lower or "sign-in" in stuck_url_lower or "ap/signin" in stuck_url_lower:
                        if "cannot find" in stuck_text or "no account" in stuck_text or phone_retries >= 2:
                            app.log("   STUCK on sign-in with 'cannot find account' → SKIP")
                            app.update_status("Sign-in stuck - SKIP", "red")
                            app._last_result = "SKIP_VERIFICATION"
                            return
                        app.log("   STUCK on sign-in → going back to register...")
                        await page.goto(AMAZON_REGISTER_URL, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(3000)
                        # Try to click Create
                        for cs in ["a:has-text('Create your Amazon Developer account')",
                                    "button:has-text('Create your Amazon Developer account')",
                                    "a[id='createAccountSubmit']", "a:has-text('Create account')"]:
                            try:
                                el = page.locator(cs).first
                                if await el.is_visible():
                                    # Don't click submit on registration form
                                    name_exists = await page.query_selector("#ap_customer_name")
                                    if name_exists:
                                        break
                                    await el.click()
                                    app.log(f"   Clicked: {cs}")
                                    await page.wait_for_timeout(3000)
                                    break
                            except Exception:
                                continue
                        _stuck_count = 0
                        continue

                    # On amazon.com homepage → go to register
                    elif "amazon.com" in stuck_url_lower and "/ap/" not in stuck_url_lower and "developer" not in stuck_url_lower:
                        app.log("   STUCK on Amazon homepage → going to register...")
                        await page.goto(AMAZON_REGISTER_URL, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(3000)
                        _stuck_count = 0
                        continue

                    # On developer.amazon.com → probably done, break
                    elif "developer.amazon.com" in stuck_url_lower and "registration" not in stuck_url_lower:
                        app.log("   On Developer dashboard → seems done!")
                        break

                    # Password re-entry needed
                    elif "password" in stuck_text[:500] or await page.query_selector("input[type='password']"):
                        app.log("   STUCK: password re-entry needed...")
                        pw_el = None
                        for sel in ["#ap_password", "input[type='password']"]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible():
                                    pw_el = el
                                    break
                            except Exception:
                                continue
                        if pw_el:
                            await pw_el.click()
                            await page.keyboard.type(out_pass, delay=80)
                            for btn in ["#signInSubmit", "input[type='submit']", "button[type='submit']"]:
                                try:
                                    el = page.locator(btn).first
                                    if await el.is_visible():
                                        await el.click()
                                        break
                                except Exception:
                                    continue
                            await page.wait_for_timeout(4000)
                        _stuck_count = 0
                        continue

                    # Unknown page → refresh
                    else:
                        app.log(f"   STUCK on unknown page → refreshing... ({cur_url[:60]})")
                        await page.reload(wait_until="domcontentloaded", timeout=20000)
                        await page.wait_for_timeout(3000)
                        _stuck_count = 0
                        continue

                await page.wait_for_timeout(1000)

            flog(f"OTP loop done. otp_found={otp_found is not None}, otp_sel={otp_sel}")
            if not otp_found:
                flog("NO OTP FOUND - returning")
                app.log("No OTP - logged in!")
                app.update_status("DONE - No OTP needed", "green")
                if not getattr(app, '_batch_mode', False):
                    app.root.after(0, lambda: messagebox.showinfo("Najah!", "Dkhelna! Ma tlabach OTP."))
                return

            flog("=== OUTLOOK FLOW START ===")
            app.log("OTP requested! Tab 2 = Outlook...")
            otp = None
            try:
                flog("Opening new page for Outlook...")
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

                # Dismiss passkey/interrupt/"Stay signed in?" — loop until clear
                for _ in range(8):
                    await page_outlook.wait_for_timeout(2000)
                    cur_url = page_outlook.url.lower()
                    dismissed = False
                    # Passkey or interrupt page
                    if "passkey" in cur_url or "interrupt" in cur_url or "kmsi" in cur_url:
                        app.log(f"   Passkey/interrupt/KMSI page — dismissing... ({page_outlook.url[:60]})")
                        for sel in ["#idBtn_Back", "button:has-text('Cancel')", "button:has-text('Annuler')",
                                    "button:has-text('Skip for now')", "button:has-text('Skip')",
                                    "button:has-text('Not now')", "button:has-text('No')",
                                    "a:has-text('Cancel')", "a:has-text('Annuler')",
                                    "a:has-text('Skip for now')", "#cancelBtn",
                                    "button[aria-label='Cancel']", "button[aria-label='No']"]:
                            try:
                                el = page_outlook.locator(sel).first
                                if await el.is_visible():
                                    await el.click()
                                    dismissed = True
                                    app.log(f"   Dismissed: {sel}")
                                    await page_outlook.wait_for_timeout(2000)
                                    break
                            except Exception:
                                continue
                        if not dismissed:
                            # Try Escape key as fallback
                            await page_outlook.keyboard.press("Escape")
                            app.log("   Pressed Escape")
                            await page_outlook.wait_for_timeout(2000)
                        continue
                    # "Stay signed in?" dialog
                    try:
                        stay_btn = page_outlook.locator("#idBtn_Back").first
                        if await stay_btn.is_visible():
                            await stay_btn.click()
                            app.log("   'Stay signed in?' → No")
                            await page_outlook.wait_for_timeout(2000)
                            continue
                    except Exception:
                        pass
                    # Clear — no more dialogs
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

                # Dismiss "newest Outlook" popup (No thanks / 不，谢谢 / Non merci / etc)
                for dismiss_sel in [
                    "button:has-text('No, thanks')", "button:has-text('No thanks')",
                    "button:has-text('不，谢谢')", "button:has-text('Non, merci')",
                    "button:has-text('Non merci')", "button:has-text('Nein, danke')",
                    "button:has-text('No, gracias')", "button:has-text('Niet, bedankt')",
                    "a:has-text('No, thanks')", "a:has-text('不，谢谢')",
                    "button[aria-label*='No']", "button[aria-label*='dismiss']",
                    "button[aria-label*='close']", "button[aria-label*='Cancel']",
                ]:
                    try:
                        el = page_outlook.locator(dismiss_sel).first
                        if await el.is_visible():
                            await el.click()
                            app.log(f"   Outlook popup dismissed: {dismiss_sel}")
                            await page_outlook.wait_for_timeout(2000)
                            break
                    except Exception:
                        continue

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

                # OTP search with resend retry (max 3 attempts)
                otp_matches = []
                for otp_attempt in range(3):
                    if otp_attempt > 0:
                        # Resend OTP from Amazon page
                        app.log(f"   OTP attempt {otp_attempt+1}/3 - Resend OTP mn Amazon...")
                        await page.bring_to_front()
                        await page.wait_for_timeout(1000)
                        resent = False
                        for resend_sel in [
                            "a:has-text('Resend OTP')",
                            "a:has-text('Resend the code')",
                            "a:has-text('Send again')",
                            "a:has-text('Resend')",
                            "button:has-text('Resend OTP')",
                            "button:has-text('Resend')",
                            "button:has-text('Send again')",
                            "a[id*='resend']",
                            "button[id*='resend']",
                            "#cvf-resend-link",
                        ]:
                            try:
                                el = page.locator(resend_sel).first
                                if await el.is_visible():
                                    await el.click()
                                    app.log(f"   Clicked resend: {resend_sel}")
                                    resent = True
                                    break
                            except Exception:
                                continue
                        if not resent:
                            app.log("   Resend button mal9ach!")
                        await page.wait_for_timeout(8000)
                        # Go back to Outlook
                        await page_outlook.bring_to_front()
                        await page_outlook.wait_for_timeout(2000)
                        # Refresh inbox
                        await page_outlook.goto("https://outlook.live.com/mail/0/inbox", wait_until="domcontentloaded", timeout=30000)
                        await page_outlook.wait_for_timeout(5000)
                        # Search Amazon again
                        for sel in ["#topSearchInput", "input[aria-label*='Search']", "input[placeholder*='Search']", "input[placeholder*='Rechercher']"]:
                            try:
                                s = page_outlook.locator(sel).first
                                if await s.is_visible():
                                    await s.click()
                                    await page_outlook.wait_for_timeout(500)
                                    await page_outlook.keyboard.type("Amazon", delay=80)
                                    await page_outlook.keyboard.press("Enter")
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

                    # If Amazon email not found → resend from Amazon and retry
                    if not amazon_clicked:
                        app.log(f"   Attempt {otp_attempt+1}: Amazon email mal9ach f Outlook — resend...")
                        continue

                    await page_outlook.wait_for_timeout(3000)

                    # OTP: nakhdo HTML dyal l-page
                    msg_body = await page_outlook.content()
                    app.log("   Qrina HTML dyal page")

                    # L9 OTP 9dam "One Time Password" wla "security code"
                    otp_context = re.search(r'(?:One Time Password|security code|OTP)[^\d]{0,100}(\d{6})', msg_body, re.IGNORECASE | re.DOTALL)
                    if otp_context:
                        otp_matches = [otp_context.group(1)]
                        app.log(f"   OTP mn context: {otp_matches[0]}")
                        break
                    else:
                        clean_body = re.sub(r'#[0-9a-fA-F]{6}', '', msg_body)
                        otp_matches = re.findall(r"\b\d{6}\b", clean_body)
                        if not otp_matches:
                            otp_matches = re.findall(r"\b\d{4,8}\b", clean_body)
                    if otp_matches:
                        app.log(f"   OTP l9inah: {otp_matches[0]}")
                        break
                    else:
                        app.log(f"   Attempt {otp_attempt+1}: OTP mal9ach f email...")

                if not otp_matches:
                    is_batch = getattr(app, '_batch_mode', False)
                    if is_batch:
                        app.log("   OTP mal9ach ba3d 3 attempts - SKIP")
                        raise Exception("OTP not found after 3 resend attempts")
                    else:
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
                flog(f"OUTLOOK ERROR: {outlook_err}")
                flog(traceback.format_exc())
                app.log(f"OUTLOOK ERROR: {outlook_err}")
                app.log(traceback.format_exc()[:500])
                # If OTP not found via Outlook, ask manually (or skip in batch)
                if not otp:
                    is_batch = getattr(app, '_batch_mode', False)
                    if is_batch:
                        app.log("Outlook ma khdamch - SKIP (batch mode)")
                        app._last_result = "SKIP_VERIFICATION"
                    else:
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
            flog(f"OTP paste check: otp={otp}, otp_found={otp_found is not None}, otp_sel={otp_sel}")
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

                        # CHECK "cannot find account" before trying password
                        try:
                            _login_text = (await page.inner_text("body")).lower() if await page.query_selector("body") else ""
                        except Exception:
                            _login_text = ""
                        if ("cannot find" in _login_text or "can\u2019t find" in _login_text or
                            "no account found" in _login_text):
                            app.log("'Cannot find account' on dev portal login → SKIP.")
                            app.update_status("Cannot find account - SKIP", "orange")
                            app._last_result = "phone"
                            return

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

                        # CHECK AGAIN after login attempt
                        try:
                            _login_text2 = (await page.inner_text("body")).lower() if await page.query_selector("body") else ""
                        except Exception:
                            _login_text2 = ""
                        if ("cannot find" in _login_text2 or "can\u2019t find" in _login_text2 or
                            "no account found" in _login_text2):
                            app.log("'Cannot find account' after login → SKIP.")
                            app.update_status("Cannot find account - SKIP", "orange")
                            app._last_result = "phone"
                            return
                        if "signin" in page.url.lower() or "sign-in" in page.url.lower():
                            # Still on sign-in page = login failed
                            app.log("Still on sign-in after login attempt → SKIP.")
                            app.update_status("Login failed - SKIP", "orange")
                            app._last_result = "phone"
                            return

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
                                           "Belgium": "BE", "Poland": "PL", "Turkey": "TR",
                                           "Denmark": "DK", "Finland": "FI", "Croatia": "HR",
                                           "Luxembourg": "LU", "Portugal": "PT", "Austria": "AT",
                                           "Greece": "GR"}
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
                                  "Belgium": "BE (+32)", "Poland": "PL (+48)", "Turkey": "TR (+90)",
                                  "Denmark": "DK (+45)", "Finland": "FI (+358)", "Croatia": "HR (+385)",
                                  "Luxembourg": "LU (+352)", "Portugal": "PT (+351)", "Austria": "AT (+43)",
                                  "Greece": "GR (+30)"}
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

                # ====== 2FA AUTHENTICATOR SETUP (same session) ======
                AMAZON_2FA_URL = "https://www.amazon.com/a/settings/approval/setup/register?openid.mode=checkid_setup&ref_=ax_am_landing_add_2sv&openid.assoc_handle=usflex&openid.ns=http://specs.openid.net/auth/2.0"
                if not getattr(app, '_stop_flag', False):
                    app.log("2FA: Session active — going to authenticator setup...")
                    app.update_status("2FA Setup...", "orange")
                    app._2fa_totp_secret = None

                    for _2fa_try in range(3):
                        if getattr(app, '_stop_flag', False):
                            break
                        if _2fa_try > 0:
                            app.log(f"2FA: Retry {_2fa_try+1}/3...")
                            await page.wait_for_timeout(3000)

                        await page.goto(AMAZON_2FA_URL, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(4000)

                        # Handle password re-entry or sign-in if needed
                        for _auth in range(3):
                            cur = page.url.lower()
                            if "approval" in cur or "settings" in cur or "mfa" in cur:
                                break
                            # Password field
                            pw_2fa = None
                            for sel in ["#ap_password", "input[type='password']"]:
                                try:
                                    el = page.locator(sel).first
                                    if await el.is_visible():
                                        pw_2fa = el
                                        break
                                except Exception:
                                    continue
                            if pw_2fa:
                                app.log("2FA: Re-entering password...")
                                await pw_2fa.click()
                                await page.wait_for_timeout(200)
                                await page.keyboard.type(out_pass, delay=80)
                                for btn in ["#signInSubmit", "input[type='submit']", "button[type='submit']"]:
                                    try:
                                        el = page.locator(btn).first
                                        if await el.is_visible():
                                            await el.click()
                                            break
                                    except Exception:
                                        continue
                                await page.wait_for_timeout(4000)
                                continue
                            break

                        app.log(f"2FA: URL = {page.url[:80]}")

                        # Select Authenticator App option
                        for sel in ["input[value='authenticator']", "input[type='radio'][value*='auth']",
                                    "input[type='radio'][value*='totp']", "#auth-TOTP",
                                    "label:has-text('Authenticator App')", "label:has-text('authenticator')",
                                    "a:has-text('Authenticator App')"]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible():
                                    await el.click()
                                    app.log(f"2FA: Selected: {sel}")
                                    await page.wait_for_timeout(2000)
                                    break
                            except Exception:
                                continue

                        # Click "Can't scan the barcode?"
                        for sel in ["a:has-text(\"Can't scan the barcode\")", "a:has-text(\"Can't scan\")",
                                    "a:has-text('enter a key')", "a:has-text('enter it manually')",
                                    "a:has-text('manually enter')", "a:has-text('barcode')",
                                    "button:has-text(\"Can't scan\")", "span:has-text(\"Can't scan\")"]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible():
                                    await el.click()
                                    app.log(f"2FA: Clicked: {sel}")
                                    await page.wait_for_timeout(3000)
                                    break
                            except Exception:
                                continue

                        # Extract TOTP secret
                        secret = None
                        FAKE_SECRETS = {"entermobilenumberoremail", "enteremailormobilenumber",
                                       "signinorcreateaccount", "continuetosignin", "createaccount"}
                        for sel in ["#totp-secret", "#secret-key", "input[id*='secret']", "input[readonly]",
                                    "code", "kbd", "pre", ".a-text-bold", "span.a-text-bold",
                                    "#auth-mfa-setup-description b", "#auth-mfa-setup-description strong",
                                    "div.a-alert-content b", "b", "strong"]:
                            try:
                                elements = page.locator(sel)
                                count = await elements.count()
                                for i in range(min(count, 10)):
                                    el = elements.nth(i)
                                    if await el.is_visible():
                                        text = await el.input_value() if sel.startswith("input") else await el.inner_text()
                                        clean = text.strip().replace(" ", "").replace("-", "")
                                        if 16 <= len(clean) <= 52 and re.match(r'^[A-Za-z2-7]+$', clean):
                                            if clean.lower() not in FAKE_SECRETS:
                                                has_digits = any(c in '234567' for c in clean)
                                                is_word = clean.lower().isalpha() and len(clean) < 30
                                                if has_digits or not is_word:
                                                    secret = clean.upper()
                                                    app.log(f"2FA: Secret found: {secret[:4]}...{secret[-4:]}")
                                                    break
                            except Exception:
                                continue
                            if secret:
                                break

                        # Regex fallback from page text
                        if not secret:
                            try:
                                pg_text = await page.inner_text("body")
                                matches = re.findall(r'\b([A-Z2-7]{16,52})\b', pg_text)
                                real = [m for m in matches if any(c in '234567' for c in m)]
                                if not real:
                                    real = [m for m in matches if not m.isalpha()]
                                if real:
                                    secret = max(real, key=len)
                                    app.log(f"2FA: Secret (regex): {secret[:4]}...{secret[-4:]}")
                                else:
                                    matches2 = re.findall(r'([A-Z2-7]{4}[\s]+[A-Z2-7]{4}[\s]+[A-Z2-7]{4}[\s]+[A-Z2-7]{4,})', pg_text)
                                    if matches2:
                                        secret = matches2[0].replace(" ", "")
                            except Exception:
                                pass

                        if not secret:
                            app.log(f"2FA: Secret not found (attempt {_2fa_try+1})")
                            try:
                                await page.screenshot(path=os.path.join(BASE_DIR, f"2fa_fail_{email.split('@')[0]}.png"), full_page=True)
                            except Exception:
                                pass
                            continue

                        # Generate TOTP code and verify
                        try:
                            import pyotp
                        except ImportError:
                            subprocess.run([sys.executable, "-m", "pip", "install", "pyotp"], capture_output=True, timeout=30)
                            import pyotp
                        totp_obj = pyotp.TOTP(secret)
                        code_2fa = totp_obj.now()
                        app.log(f"2FA: Code = {code_2fa}")

                        # Enter code
                        for sel in ["#auth-mfa-otpcode", "input[name='otpCode']", "input[name='code']",
                                    "input[placeholder*='code']", "input[type='tel']", "input[maxlength='6']"]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible():
                                    await el.fill("")
                                    await pw_human_type(page, sel, code_2fa)
                                    app.log(f"2FA: Entered in: {sel}")
                                    break
                            except Exception:
                                continue
                        await page.wait_for_timeout(1000)

                        # Click verify
                        for btn in ["#auth-mfa-remember-device-submit", "button:has-text('Verify OTP')",
                                    "button:has-text('Verify')", "input[type='submit']", "button[type='submit']"]:
                            try:
                                el = page.locator(btn).first
                                if await el.is_visible():
                                    await el.click()
                                    app.log(f"2FA: Clicked: {btn}")
                                    break
                            except Exception:
                                continue
                        await page.wait_for_timeout(5000)

                        # Check success
                        try:
                            r_text = await page.inner_text("body")
                            if any(kw in r_text.lower() for kw in ["two-step verification", "success", "enabled", "done", "got it"]):
                                app.log(f"2FA: SUCCESS for {email}!")
                                for btn in ["button:has-text('Got it')", "button:has-text('Done')",
                                            "a:has-text('Got it')", "a:has-text('Done')"]:
                                    try:
                                        el = page.locator(btn).first
                                        if await el.is_visible():
                                            await el.click()
                                            break
                                    except Exception:
                                        continue
                        except Exception:
                            pass

                        app._2fa_totp_secret = secret
                        app.update_status(f"2FA OK: {email}", "green")
                        app.log(f"2FA: TOTP secret saved for {email}")
                        break

                    if not getattr(app, '_2fa_totp_secret', None):
                        app.log(f"2FA: FAILED after 3 attempts for {email}")
                # ====== END 2FA ======

            elif not otp:
                app.log("OTP manl9awch - account SKIP")

    except Exception as e:
        import traceback
        flog(f"OUTER EXCEPTION: {type(e).__name__}: {e}")
        flog(traceback.format_exc())
        if "TargetClosedError" in type(e).__name__ or "closed" in str(e).lower():
            app.log("Chrome tsad - normal.")
        else:
            app.log(f"Khata: {e}")
            app.log(traceback.format_exc()[:500])
    finally:
        flog("=== FINALLY BLOCK ===")
        is_batch = getattr(app, '_batch_mode', False)
        if is_batch:
            app.log("Closing Chrome...")
            # Kill only bot's Chrome by PID, not user's Chrome
            _pid = getattr(app, '_browser_pid', None)
            if _pid:
                try:
                    import subprocess as _sp
                    _sp.run(["taskkill", "/F", "/T", "/PID", str(_pid)], capture_output=True, timeout=5)
                    flog(f"Killed bot Chrome PID {_pid}")
                except Exception:
                    pass
                app._browser_pid = None
            try:
                await asyncio.wait_for(p.stop(), timeout=5)
            except Exception:
                pass
            flog("=== FINALLY DONE (batch) ===")
        else:
            try:
                app.log("Chrome m7all - Siftu b l'id (X) melli t7ab.")
                if browser.is_connected():
                    while browser.is_connected():
                        await asyncio.sleep(1)
            except Exception:
                pass

async def run_2fa_only(app, email, out_pass):
    """Run 2FA authenticator setup only — for accounts already created (status=ok)"""
    from playwright.async_api import async_playwright
    AMAZON_2FA_URL = "https://www.amazon.com/a/settings/approval/setup/register?openid.mode=checkid_setup&ref_=ax_am_landing_add_2sv&openid.assoc_handle=usflex&openid.ns=http://specs.openid.net/auth/2.0"
    app.update_status(f"2FA: {email}...", "orange")
    app.log(f"2FA-only: Launching Chrome for {email}...")
    app._2fa_totp_secret = None

    p = await async_playwright().start()
    try:
        try:
            browser = await p.chromium.launch(headless=False, channel="chrome")
        except Exception:
            browser = await p.chromium.launch(headless=False)
        app._current_browser = browser
        try:
            app._browser_pid = browser.process.pid
        except Exception:
            app._browser_pid = None

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Step 1: Sign in to Amazon using the regular sign-in page (NOT developer portal)
        AMAZON_SIGNIN = "https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3Fref_%3Dnav_custrec_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
        app.log("2FA: Going to Amazon sign-in page...")
        await page.goto(AMAZON_SIGNIN, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Enter email
        app.log("2FA: Entering email...")
        await page.wait_for_timeout(2000)
        for sel in ["#ap_email", "input[name='email']", "input[type='email']",
                    "input[placeholder*='email']", "input[placeholder*='mobile']"]:
            try:
                el = page.locator(sel).first
                if await el.is_visible():
                    await el.click()
                    await page.wait_for_timeout(300)
                    await el.fill("")
                    await el.type(email, delay=80)
                    app.log(f"2FA: Email OK")
                    break
            except Exception:
                continue
        await page.wait_for_timeout(1000)

        # Click Continue
        for btn in ["#continue", "input[type='submit']", "button:has-text('Continue')"]:
            try:
                el = page.locator(btn).first
                if await el.is_visible():
                    await el.click()
                    break
            except Exception:
                continue
        await page.wait_for_timeout(4000)

        # Wait for password field and enter password
        app.log("2FA: Waiting for password field...")
        for _pw_try in range(5):
            try:
                pw_el = page.locator("#ap_password").first
                if await pw_el.is_visible():
                    await pw_el.click()
                    await page.wait_for_timeout(300)
                    await pw_el.fill("")
                    await pw_el.type(out_pass, delay=80)
                    app.log("2FA: Password OK")
                    break
            except Exception:
                pass
            try:
                pw_el = page.locator("input[type='password']").first
                if await pw_el.is_visible():
                    await pw_el.click()
                    await page.wait_for_timeout(300)
                    await pw_el.fill("")
                    await pw_el.type(out_pass, delay=80)
                    app.log("2FA: Password OK (generic)")
                    break
            except Exception:
                pass
            app.log(f"2FA: Password field not found yet ({_pw_try+1}/5)")
            await page.wait_for_timeout(2000)
        await page.wait_for_timeout(500)

        # Click Sign in
        for btn in ["#signInSubmit", "input[type='submit']", "button[type='submit']", "button:has-text('Sign in')"]:
            try:
                el = page.locator(btn).first
                if await el.is_visible():
                    await el.click()
                    app.log("2FA: Sign in clicked")
                    break
            except Exception:
                continue
        await page.wait_for_timeout(5000)
        app.log(f"2FA: Login done. URL={page.url[:60]}")

        # Step 2: Now signed in — go to 2FA setup page
        app.log("2FA: Signed in — navigating to 2FA setup...")
        for _2fa_try in range(3):
            if getattr(app, '_stop_flag', False):
                break
            if _2fa_try > 0:
                app.log(f"2FA: Retry {_2fa_try+1}/3...")
                await page.wait_for_timeout(3000)

            await page.goto(AMAZON_2FA_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(4000)

            # Handle password re-entry
            for _auth in range(3):
                cur = page.url.lower()
                if "approval" in cur or "settings" in cur or "mfa" in cur:
                    break
                pw_2fa = None
                for sel in ["#ap_password", "input[type='password']"]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible():
                            pw_2fa = el
                            break
                    except Exception:
                        continue
                if pw_2fa:
                    app.log("2FA: Re-entering password...")
                    await pw_2fa.click()
                    await page.wait_for_timeout(200)
                    await page.keyboard.type(out_pass, delay=80)
                    for btn in ["#signInSubmit", "input[type='submit']", "button[type='submit']"]:
                        try:
                            el = page.locator(btn).first
                            if await el.is_visible():
                                await el.click()
                                break
                        except Exception:
                            continue
                    await page.wait_for_timeout(4000)
                    continue
                break

            app.log(f"2FA: URL = {page.url[:80]}")

            # Select Authenticator App
            for sel in ["input[value='authenticator']", "input[type='radio'][value*='auth']",
                        "input[type='radio'][value*='totp']", "#auth-TOTP",
                        "label:has-text('Authenticator App')", "label:has-text('authenticator')",
                        "a:has-text('Authenticator App')"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible():
                        await el.click()
                        app.log(f"2FA: Selected: {sel}")
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

            # Click "Can't scan the barcode?"
            for sel in ["a:has-text(\"Can't scan the barcode\")", "a:has-text(\"Can't scan\")",
                        "a:has-text('enter a key')", "a:has-text('enter it manually')",
                        "a:has-text('manually enter')", "a:has-text('barcode')",
                        "button:has-text(\"Can't scan\")", "span:has-text(\"Can't scan\")"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible():
                        await el.click()
                        app.log(f"2FA: Clicked: {sel}")
                        await page.wait_for_timeout(3000)
                        break
                except Exception:
                    continue

            # Extract TOTP secret
            secret = None
            FAKE_SECRETS = {"entermobilenumberoremail", "enteremailormobilenumber",
                           "signinorcreateaccount", "continuetosignin", "createaccount"}
            for sel in ["#totp-secret", "#secret-key", "input[id*='secret']", "input[readonly]",
                        "code", "kbd", "pre", ".a-text-bold", "span.a-text-bold",
                        "#auth-mfa-setup-description b", "#auth-mfa-setup-description strong",
                        "div.a-alert-content b", "b", "strong"]:
                try:
                    elements = page.locator(sel)
                    count = await elements.count()
                    for i in range(min(count, 10)):
                        el = elements.nth(i)
                        if await el.is_visible():
                            text = await el.input_value() if sel.startswith("input") else await el.inner_text()
                            clean = text.strip().replace(" ", "").replace("-", "")
                            if 16 <= len(clean) <= 52 and re.match(r'^[A-Za-z2-7]+$', clean):
                                if clean.lower() not in FAKE_SECRETS:
                                    has_digits = any(c in '234567' for c in clean)
                                    is_word = clean.lower().isalpha() and len(clean) < 30
                                    if has_digits or not is_word:
                                        secret = clean.upper()
                                        app.log(f"2FA: Secret found: {secret[:4]}...{secret[-4:]}")
                                        break
                except Exception:
                    continue
                if secret:
                    break

            # Regex fallback
            if not secret:
                try:
                    pg_text = await page.inner_text("body")
                    matches = re.findall(r'\b([A-Z2-7]{16,52})\b', pg_text)
                    real = [m for m in matches if any(c in '234567' for c in m)]
                    if not real:
                        real = [m for m in matches if not m.isalpha()]
                    if real:
                        secret = max(real, key=len)
                        app.log(f"2FA: Secret (regex): {secret[:4]}...{secret[-4:]}")
                    else:
                        matches2 = re.findall(r'([A-Z2-7]{4}[\s]+[A-Z2-7]{4}[\s]+[A-Z2-7]{4}[\s]+[A-Z2-7]{4,})', pg_text)
                        if matches2:
                            secret = matches2[0].replace(" ", "")
                except Exception:
                    pass

            if not secret:
                app.log(f"2FA: Secret not found (attempt {_2fa_try+1})")
                continue

            # Generate TOTP code and verify
            try:
                import pyotp
            except ImportError:
                subprocess.run([sys.executable, "-m", "pip", "install", "pyotp"], capture_output=True, timeout=30)
                import pyotp
            totp_obj = pyotp.TOTP(secret)
            code_2fa = totp_obj.now()
            app.log(f"2FA: Code = {code_2fa}")

            # Enter code
            for sel in ["#auth-mfa-otpcode", "input[name='otpCode']", "input[name='code']",
                        "input[placeholder*='code']", "input[type='tel']", "input[maxlength='6']"]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible():
                        await el.fill("")
                        await el.type(code_2fa, delay=80)
                        app.log(f"2FA: Entered in: {sel}")
                        break
                except Exception:
                    continue
            await page.wait_for_timeout(1000)

            # Click verify
            for btn in ["#auth-mfa-remember-device-submit", "button:has-text('Verify OTP')",
                        "button:has-text('Verify')", "input[type='submit']", "button[type='submit']"]:
                try:
                    el = page.locator(btn).first
                    if await el.is_visible():
                        await el.click()
                        app.log(f"2FA: Clicked: {btn}")
                        break
                except Exception:
                    continue
            await page.wait_for_timeout(5000)

            # Check success
            try:
                r_text = await page.inner_text("body")
                if any(kw in r_text.lower() for kw in ["two-step verification", "success", "enabled", "done", "got it"]):
                    app.log(f"2FA: SUCCESS for {email}!")
                    for btn in ["button:has-text('Got it')", "button:has-text('Done')",
                                "a:has-text('Got it')", "a:has-text('Done')"]:
                        try:
                            el = page.locator(btn).first
                            if await el.is_visible():
                                await el.click()
                                break
                        except Exception:
                            continue
            except Exception:
                pass

            app._2fa_totp_secret = secret
            app.update_status(f"2FA OK: {email}", "green")
            app.log(f"2FA: TOTP secret saved for {email}")
            break

        if not app._2fa_totp_secret:
            app.log(f"2FA: FAILED after 3 attempts for {email}")
            app.update_status(f"2FA FAIL: {email}", "red")

    except Exception as e:
        import traceback
        flog(f"2FA-only EXCEPTION: {type(e).__name__}: {e}")
        app.log(f"2FA Error: {e}")
    finally:
        _pid = getattr(app, '_browser_pid', None)
        if _pid:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(_pid)], capture_output=True, timeout=5)
            except Exception:
                pass
            app._browser_pid = None
        try:
            await asyncio.wait_for(p.stop(), timeout=5)
        except Exception:
            pass


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ProtonVPN + Amazon Developer + Outlook OTP")
        self.root.geometry("550x700+100+50")
        self.root.configure(padx=20, pady=15, bg="#f0f4f8")
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(1000, lambda: self.root.attributes('-topmost', False))

        # Lwan: hmar #c0392b, khdar #27ae60, zra9 #3498db, sfar #f1c40f
        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 9), background="#f0f4f8")
        style.configure("TLabelframe", background="#f0f4f8")
        style.configure("TLabelframe.Label", font=("Arial", 10, "bold"), foreground="#c0392b", background="#f0f4f8")

        ttk.Label(root, text="ProtonVPN → Amazon Developer → Outlook OTP", font=("Arial", 12, "bold"), foreground="#c0392b").pack(pady=5)

        # === 1. VPN (zra9) ===
        f_vpn = ttk.LabelFrame(root, text=" 1. VPN WireGuard (lawal) ", padding=8)
        f_vpn.pack(fill="x", pady=5)
        ttk.Label(f_vpn, text="Mode VPN:", foreground="#2980b9").grid(row=0, column=0, sticky="w", pady=2)
        self.vpn_mode = ttk.Combobox(f_vpn, width=32, state="readonly")
        self.vpn_mode['values'] = ("Auto (WireGuard)", "Connect b l'id (Manual)")
        self.vpn_mode.current(0)
        self.vpn_mode.grid(row=0, column=1, pady=2, padx=5)
        ttk.Label(f_vpn, text="Dawla (Country):", foreground="#2980b9").grid(row=1, column=0, sticky="w", pady=2)
        self.vpn_country = ttk.Entry(f_vpn, width=37)
        self.vpn_country.insert(0, "Germany")
        self.vpn_country.grid(row=1, column=1, pady=2, padx=5)
        self._active_tunnel = None

        # === 2. Batch CSV / Google Sheets ===
        f_batch = ttk.LabelFrame(root, text=" 2. Batch Mode (CSV / Google Sheets) ", padding=8)
        f_batch.pack(fill="x", pady=5)
        self.csv_path_var = tk.StringVar()
        ttk.Label(f_batch, text="Google Sheet URL\nou CSV File:", foreground="#e67e22").grid(row=0, column=0, sticky="w", pady=2)
        self.csv_entry = ttk.Entry(f_batch, width=30, textvariable=self.csv_path_var)
        self.csv_entry.grid(row=0, column=1, pady=2, padx=5)
        csv_btn_frame = tk.Frame(f_batch, bg="#f0f4f8")
        csv_btn_frame.grid(row=0, column=2, rowspan=2, padx=3)
        self.csv_browse_btn = tk.Button(csv_btn_frame, text="Browse", command=self._browse_csv, bg="#e67e22", fg="white", cursor="hand2")
        self.csv_browse_btn.pack(pady=1)
        self.sheets_refresh_btn = tk.Button(csv_btn_frame, text="Refresh", command=self._refresh_sheets, bg="#3498db", fg="white", cursor="hand2")
        self.sheets_refresh_btn.pack(pady=1)
        self.batch_progress_var = tk.StringVar(value="Paste Google Sheet URL wla Browse CSV file")
        ttk.Label(f_batch, textvariable=self.batch_progress_var, foreground="#e67e22", font=("Arial", 8)).grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

        # === Accounts Table ===
        f_table = ttk.LabelFrame(root, text=" Accounts Table ", padding=5)
        f_table.pack(fill="both", expand=True, pady=5)

        table_cols = ("check", "email", "prenom", "nom", "country", "status")
        self.acc_tree = ttk.Treeview(f_table, columns=table_cols, show="headings", height=8, selectmode="browse")
        self.acc_tree.heading("check", text="[x]")
        self.acc_tree.heading("email", text="Email")
        self.acc_tree.heading("prenom", text="Prenom")
        self.acc_tree.heading("nom", text="Nom")
        self.acc_tree.heading("country", text="Country")
        self.acc_tree.heading("status", text="Status")
        self.acc_tree.column("check", width=30, minwidth=30, anchor="center")
        self.acc_tree.column("email", width=155, minwidth=100)
        self.acc_tree.column("prenom", width=65, minwidth=50)
        self.acc_tree.column("nom", width=65, minwidth=50)
        self.acc_tree.column("country", width=85, minwidth=60)
        self.acc_tree.column("status", width=65, minwidth=50)

        tree_scroll = ttk.Scrollbar(f_table, orient="vertical", command=self.acc_tree.yview)
        self.acc_tree.configure(yscrollcommand=tree_scroll.set)
        self.acc_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        # Click row to toggle checkbox
        self.acc_tree.bind("<Button-1>", self._toggle_check)

        # Table style: color rows by status
        self.acc_tree.tag_configure("ok", background="#d5f5e3")
        self.acc_tree.tag_configure("skip", background="#fadbd8")
        self.acc_tree.tag_configure("fail", background="#f9e79f")
        self.acc_tree.tag_configure("running", background="#f9e74a")
        self.acc_tree.tag_configure("pending", background="white")
        self.acc_tree.tag_configure("checked", background="#d4efdf")

        # Track checked rows
        self._checked_rows = set()

        table_btn_frame = tk.Frame(root, bg="#f0f4f8")
        table_btn_frame.pack(pady=3)
        ttk.Label(table_btn_frame, text="Filter:", foreground="#2c3e50").pack(side="left", padx=2)
        self.filter_var = tk.StringVar(value="Empty status")
        self.filter_combo = ttk.Combobox(table_btn_frame, textvariable=self.filter_var, width=18, state="readonly")
        self.filter_combo['values'] = ("Empty status", "Retry (empty+captcha+2fa_fail)", "Need 2FA (ok)", "All accounts", "By country...")
        self.filter_combo.pack(side="left", padx=3)
        self.filter_combo.bind("<<ComboboxSelected>>", self._on_filter_change)
        self.country_filter_var = tk.StringVar(value="")
        self.country_filter_combo = ttk.Combobox(table_btn_frame, textvariable=self.country_filter_var, width=14, state="readonly")
        self.country_filter_combo.pack(side="left", padx=2)
        self.country_filter_combo.pack_forget()  # Hidden by default
        self.country_filter_combo.bind("<<ComboboxSelected>>", self._apply_country_filter)
        self.select_all_btn = tk.Button(table_btn_frame, text="Select All", command=self._select_all_accounts, bg="#3498db", fg="white", cursor="hand2", padx=8)
        self.select_all_btn.pack(side="left", padx=3)
        self.deselect_all_btn = tk.Button(table_btn_frame, text="Deselect All", command=self._deselect_all_accounts, bg="#95a5a6", fg="white", cursor="hand2", padx=8)
        self.deselect_all_btn.pack(side="left", padx=3)
        self.delete_sel_btn = tk.Button(table_btn_frame, text="Delete Selected", command=self._delete_selected_accounts, bg="#e74c3c", fg="white", cursor="hand2", padx=8)
        self.delete_sel_btn.pack(side="left", padx=3)

        # === Action Buttons ===
        btn_frame = tk.Frame(root, bg="#f0f4f8")
        btn_frame.pack(pady=8)
        self.import_btn = tk.Button(btn_frame, text="IMPORT", command=self._import_accounts,
                                   font=("Arial", 10, "bold"), bg="#27ae60", fg="white", activebackground="#1e8449",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=12, pady=6)
        self.import_btn.pack(side="left", padx=4)
        self.batch_btn = tk.Button(btn_frame, text="BATCH", command=self.start_batch,
                                   font=("Arial", 10, "bold"), bg="#e67e22", fg="white", activebackground="#d35400",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=12, pady=6)
        self.batch_btn.pack(side="left", padx=4)
        self.stop_btn = tk.Button(btn_frame, text="STOP", command=self._stop_batch,
                                   font=("Arial", 10, "bold"), bg="#c0392b", fg="white", activebackground="#e74c3c",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=12, pady=6,
                                   state="disabled")
        self.stop_btn.pack(side="left", padx=4)
        self.next_btn = tk.Button(btn_frame, text="NEXT", command=self._skip_to_next,
                                   font=("Arial", 10, "bold"), bg="#8e44ad", fg="white", activebackground="#9b59b6",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=12, pady=6,
                                   state="disabled")
        self.next_btn.pack(side="left", padx=4)
        self.twofa_btn = tk.Button(btn_frame, text="2FA", command=self._start_2fa_batch,
                                   font=("Arial", 10, "bold"), bg="#16a085", fg="white", activebackground="#1abc9c",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=12, pady=6)
        self.twofa_btn.pack(side="left", padx=4)
        self.retry_btn = tk.Button(btn_frame, text="RETRY", command=self._retry_failed,
                                   font=("Arial", 10, "bold"), bg="#2980b9", fg="white", activebackground="#2471a3",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=12, pady=6)
        self.retry_btn.pack(side="left", padx=4)
        self.reset_btn = tk.Button(btn_frame, text="RESET", command=self.reset_all,
                                   font=("Arial", 10, "bold"), bg="#e74c3c", fg="white", activebackground="#c0392b",
                                   activeforeground="white", cursor="hand2", relief="raised", bd=2, padx=12, pady=6)
        self.reset_btn.pack(side="left", padx=4)
        self._stop_flag = False
        self._skip_flag = False
        self._batch_mode = False
        self._current_browser = None
        self._batch_remaining = None

        ttk.Label(root, text="Activity Log:", foreground="#f1c40f").pack(anchor="w")
        self.log_text = tk.Text(root, height=8, width=58, font=("Consolas", 8), state="disabled", bg="#fffde7", fg="#2c3e50", insertbackground="#c0392b")
        self.log_text.pack(pady=3)

        self.status_var = tk.StringVar()
        self.status_var.set("Wajed...")
        self.status_label = ttk.Label(root, textvariable=self.status_var, foreground="#3498db", font=("Arial", 9, "italic"))
        self.status_label.pack()

    def _kill_bot_chrome(self):
        """Kill only the Chrome launched by the bot, not user's Chrome"""
        pid = getattr(self, '_browser_pid', None)
        if pid:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=5)
                flog(f"Killed Chrome PID {pid} (tree)")
            except Exception:
                pass
            self._browser_pid = None
        self._current_browser = None

    def log(self, msg):
        def _do():
            try:
                self.log_text.configure(state="normal")
                self.log_text.insert(tk.END, f"[*] {msg}\n")
                self.log_text.see(tk.END)
                self.log_text.configure(state="disabled")
            except Exception:
                pass
        self.root.after(0, _do)

    def update_status(self, text, color="blue"):
        def _do():
            try:
                self.status_var.set(text)
                self.status_label.configure(foreground=color)
            except Exception:
                pass
        self.root.after(0, _do)

    def _update_sheet_status(self, email, status):
        """Update status in Google Sheets in background thread"""
        def _do_update():
            try:
                sheet_id = self._get_sheet_id()
                if not sheet_id:
                    return

                flog(f"Sheet update: email={email}, status={status}, sheet_id={sheet_id}")

                creds_path = os.path.join(BASE_DIR, "credentials.json")
                if not os.path.exists(creds_path):
                    flog(f"credentials.json not found")
                    return

                import gspread
                from google.oauth2.service_account import Credentials

                scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
                gc = gspread.authorize(creds)
                flog(f"Sheet ID: {sheet_id}")
                sh = gc.open_by_key(sheet_id)
                ws = sh.sheet1

                all_values = ws.get_all_values()
                header = [h.lower().strip() for h in all_values[0]]

                if "status" in header:
                    status_col = header.index("status") + 1
                else:
                    status_col = len(header) + 1
                    ws.update_cell(1, status_col, "status")

                email_col = header.index("email") + 1 if "email" in header else 1
                for row_idx, row_vals in enumerate(all_values[1:], start=2):
                    cell_email = row_vals[email_col - 1].strip() if email_col - 1 < len(row_vals) else ""
                    if cell_email.lower() == email.lower():
                        ws.update_cell(row_idx, status_col, status.upper())
                        self.log(f"  Sheet updated: {email} → {status.upper()}")
                        flog(f"Sheet updated: row {row_idx}, {email} → {status}")
                        return
                flog(f"Email {email} not found in sheet")
            except Exception as e:
                flog(f"Sheet update error: {e}")
        # Run in background so it doesn't block batch
        threading.Thread(target=_do_update, daemon=True).start()

    def _update_sheet_totp(self, email, totp_secret):
        """Save TOTP secret to Google Sheets in a 'totp_secret' column (with retry)"""
        def _do_update():
            for attempt in range(3):
                try:
                    sheet_id = self._get_sheet_id()
                    if not sheet_id:
                        return

                    creds_path = os.path.join(BASE_DIR, "credentials.json")
                    if not os.path.exists(creds_path):
                        return

                    import gspread
                    from google.oauth2.service_account import Credentials

                    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
                    gc = gspread.authorize(creds)
                    sh = gc.open_by_key(sheet_id)
                    ws = sh.sheet1

                    all_values = ws.get_all_values()
                    header = [h.lower().strip() for h in all_values[0]]

                    if "totp_secret" in header:
                        totp_col = header.index("totp_secret") + 1
                    else:
                        totp_col = len(header) + 1
                        ws.update_cell(1, totp_col, "totp_secret")

                    email_col = header.index("email") + 1 if "email" in header else 1
                    for row_idx, row_vals in enumerate(all_values[1:], start=2):
                        cell_email = row_vals[email_col - 1].strip() if email_col - 1 < len(row_vals) else ""
                        if cell_email.lower() == email.lower():
                            ws.update_cell(row_idx, totp_col, totp_secret)
                            self.log(f"  Sheet TOTP saved: {email}")
                            flog(f"Sheet TOTP saved: row {row_idx}, {email}")
                            return
                    flog(f"TOTP: Email {email} not found in sheet")
                    return
                except Exception as e:
                    flog(f"Sheet TOTP error (attempt {attempt+1}/3): {e}")
                    if attempt < 2:
                        time.sleep(3)
            flog(f"Sheet TOTP FAILED after 3 attempts: {email}")
        threading.Thread(target=_do_update, daemon=True).start()

    def _update_sheet_totp_sync(self, email, totp_secret):
        """Save TOTP secret synchronously (blocks until done) — used in batch to avoid VPN disconnect"""
        for attempt in range(3):
            try:
                sheet_id = self._get_sheet_id()
                if not sheet_id:
                    return
                creds_path = os.path.join(BASE_DIR, "credentials.json")
                if not os.path.exists(creds_path):
                    return
                import gspread
                from google.oauth2.service_account import Credentials
                scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
                gc = gspread.authorize(creds)
                sh = gc.open_by_key(sheet_id)
                ws = sh.sheet1
                all_values = ws.get_all_values()
                header = [h.lower().strip() for h in all_values[0]]
                if "totp_secret" in header:
                    totp_col = header.index("totp_secret") + 1
                else:
                    totp_col = len(header) + 1
                    ws.update_cell(1, totp_col, "totp_secret")
                email_col = header.index("email") + 1 if "email" in header else 1
                for row_idx, row_vals in enumerate(all_values[1:], start=2):
                    cell_email = row_vals[email_col - 1].strip() if email_col - 1 < len(row_vals) else ""
                    if cell_email.lower() == email.lower():
                        ws.update_cell(row_idx, totp_col, totp_secret)
                        self.log(f"  Sheet TOTP saved: {email}")
                        flog(f"Sheet TOTP saved: row {row_idx}, {email}")
                        return
                flog(f"TOTP: Email {email} not found in sheet")
                return
            except Exception as e:
                flog(f"Sheet TOTP error (attempt {attempt+1}/3): {e}")
                if attempt < 2:
                    time.sleep(3)
        flog(f"Sheet TOTP FAILED after 3 attempts: {email}")

    # --- Table methods ---
    def _populate_table(self):
        """Fill accounts table from self.batch_rows"""
        for item in self.acc_tree.get_children():
            self.acc_tree.delete(item)
        self._checked_rows = set()
        if not hasattr(self, 'batch_rows') or not self.batch_rows:
            return
        for i, row in enumerate(self.batch_rows):
            email = row.get("email", "").strip()
            prenom = row.get("prenom", row.get("first_name", "")).strip()
            nom = row.get("nom", row.get("last_name", "")).strip()
            country = row.get("country", "").strip()
            status = row.get("_status", "pending")
            self.acc_tree.insert("", "end", iid=str(i), values=("[ ]", email, prenom, nom, country, status), tags=(status,))

    def _on_filter_change(self, event=None):
        """Handle filter dropdown change"""
        val = self.filter_var.get()
        if val == "By country...":
            # Show country dropdown with available countries
            countries = set()
            if hasattr(self, '_all_rows_unfiltered') and self._all_rows_unfiltered:
                for r in self._all_rows_unfiltered:
                    c = r.get("country", "").strip()
                    if c:
                        countries.add(c)
            self.country_filter_combo['values'] = sorted(countries)
            self.country_filter_combo.pack(side="left", padx=2, before=self.select_all_btn)
        else:
            self.country_filter_combo.pack_forget()
            self._apply_filter()

    def _apply_country_filter(self, event=None):
        """Filter table by selected country"""
        self._apply_filter()

    def _apply_filter(self):
        """Apply current filter to loaded data"""
        if not hasattr(self, '_all_rows_unfiltered') or not self._all_rows_unfiltered:
            return
        filt = self.filter_var.get()
        rows = self._all_rows_unfiltered
        RETRY_STATUSES = {"", "captcha", "2fa_fail"}
        if filt == "Empty status":
            filtered = [r for r in rows if not r.get("status", "").strip()]
        elif filt.startswith("Retry"):
            filtered = [r for r in rows if r.get("status", "").strip().lower() in RETRY_STATUSES]
        elif filt.startswith("Need 2FA"):
            filtered = [r for r in rows if r.get("status", "").strip().lower() in ("ok", "2fa_fail")]
        elif filt == "All accounts":
            filtered = list(rows)
        elif filt == "By country...":
            country = self.country_filter_var.get().strip()
            if country:
                filtered = [r for r in rows if r.get("status", "").strip().lower() in RETRY_STATUSES and r.get("country", "").strip() == country]
            else:
                filtered = [r for r in rows if not r.get("status", "").strip()]
        else:
            filtered = [r for r in rows if not r.get("status", "").strip()]

        self.batch_rows = filtered
        self.batch_progress_var.set(f"{len(filtered)} accounts (from {len(rows)})")
        self.log(f"Filter '{filt}': {len(filtered)} accounts")
        self._populate_table()

    def _remove_table_row(self, idx):
        """Remove a processed row from table (thread-safe, doesn't touch sheets)"""
        def _do():
            iid = str(idx)
            try:
                if self.acc_tree.exists(iid):
                    self.acc_tree.delete(iid)
                self._checked_rows.discard(idx)
            except Exception:
                pass
        self.root.after(0, _do)

    def _update_table_status(self, idx, status):
        """Update status column and color for a row (thread-safe)"""
        def _do():
            iid = str(idx)
            try:
                vals = list(self.acc_tree.item(iid, "values"))
                vals[5] = status
                self.acc_tree.item(iid, values=vals, tags=(status,))
                self.acc_tree.see(iid)
            except Exception:
                pass
        self.root.after(0, _do)

    def _toggle_check(self, event):
        """Toggle checkbox when clicking a row"""
        region = self.acc_tree.identify_region(event.x, event.y)
        if region == "heading":
            return
        iid = self.acc_tree.identify_row(event.y)
        if not iid:
            return
        idx = int(iid)
        vals = list(self.acc_tree.item(iid, "values"))
        if idx in self._checked_rows:
            self._checked_rows.discard(idx)
            vals[0] = "[ ]"
            status = vals[5] if len(vals) > 5 else "pending"
            self.acc_tree.item(iid, values=vals, tags=(status,))
        else:
            self._checked_rows.add(idx)
            vals[0] = "[X]"
            self.acc_tree.item(iid, values=vals, tags=("checked",))
        count = len(self._checked_rows)
        total = len(getattr(self, 'batch_rows', []))
        if count > 0:
            self.batch_progress_var.set(f"{count} selected / {total} total")
        else:
            self.batch_progress_var.set(f"{total} accounts loaded")

    def _select_all_accounts(self):
        for iid in self.acc_tree.get_children():
            idx = int(iid)
            self._checked_rows.add(idx)
            vals = list(self.acc_tree.item(iid, "values"))
            vals[0] = "[X]"
            self.acc_tree.item(iid, values=vals, tags=("checked",))
        total = len(getattr(self, 'batch_rows', []))
        self.batch_progress_var.set(f"{len(self._checked_rows)} selected / {total} total")

    def _deselect_all_accounts(self):
        for iid in self.acc_tree.get_children():
            vals = list(self.acc_tree.item(iid, "values"))
            vals[0] = "[ ]"
            status = vals[5] if len(vals) > 5 else "pending"
            self.acc_tree.item(iid, values=vals, tags=(status,))
        self._checked_rows.clear()
        total = len(getattr(self, 'batch_rows', []))
        self.batch_progress_var.set(f"{total} accounts loaded")

    def _delete_selected_accounts(self):
        if not self._checked_rows:
            messagebox.showinfo("Info", "Ma selectiti hta account! Click 3la row bach t-selectih.")
            return
        count = len(self._checked_rows)
        if not messagebox.askyesno("Delete", f"Bghiti t7yad {count} account(s)?"):
            return
        indices = sorted(self._checked_rows, reverse=True)
        for idx in indices:
            if hasattr(self, 'batch_rows') and idx < len(self.batch_rows):
                self.batch_rows.pop(idx)
        self._populate_table()
        remaining = len(getattr(self, 'batch_rows', []))
        self.batch_progress_var.set(f"{remaining} accounts loaded")
        self.log(f"Deleted {count} account(s). {remaining} remaining.")

    def _stop_batch(self):
        """Stop batch processing immediately"""
        self._stop_flag = True
        self._skip_flag = True
        self.log("STOP!")
        self.update_status("STOPPED", "red")
        self.stop_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self._kill_bot_chrome()
        self._wg_disconnect()

    def _skip_to_next(self):
        """Skip current account and move to next"""
        self._skip_flag = True
        self.log("NEXT requested! Kaydouz l account li ba3d...")
        self.update_status("Skipping to next...", "orange")
        self._kill_bot_chrome()

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

    def _get_wg_configs(self, country):
        """Find WireGuard config files for a country, return list of paths"""
        code = COUNTRY_TO_CODE.get(country, country.upper()[:2])
        configs = []
        if os.path.isdir(VPN_CONFIGS_DIR):
            for f in os.listdir(VPN_CONFIGS_DIR):
                if not f.endswith(".conf"):
                    continue
                if f"wg-{code}-" in f or f.startswith(f"{country}"):
                    configs.append(os.path.join(VPN_CONFIGS_DIR, f))
        return configs

    def _wg_disconnect(self):
        """Disconnect ALL WireGuard tunnels (active + leftover)"""
        # First disconnect tracked tunnel
        tunnel = getattr(self, '_active_tunnel', None)
        if tunnel:
            try:
                flog(f"WG disconnect: {tunnel}")
                subprocess.run([WIREGUARD_EXE, "/uninstalltunnelservice", tunnel],
                              capture_output=True, timeout=10)
            except Exception as e:
                flog(f"WG disconnect error: {e}")
            self._active_tunnel = None

        # Clean up ALL leftover WireGuard tunnel services
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-Service -Name 'WireGuardTunnel*' | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                for svc in result.stdout.strip().splitlines():
                    svc = svc.strip()
                    if svc.startswith("WireGuardTunnel$"):
                        tname = svc.replace("WireGuardTunnel$", "")
                        try:
                            flog(f"WG cleanup leftover: {tname}")
                            subprocess.run([WIREGUARD_EXE, "/uninstalltunnelservice", tname],
                                          capture_output=True, timeout=10)
                        except Exception:
                            pass
        except Exception as e:
            flog(f"WG cleanup error: {e}")
        time.sleep(2)

    def _wg_connect(self, conf_path):
        """Connect WireGuard using a config file. Returns True if successful."""
        # Disconnect any existing tunnel first
        if getattr(self, '_active_tunnel', None):
            self._wg_disconnect()

        tunnel_name = os.path.splitext(os.path.basename(conf_path))[0]
        tunnel_name = tunnel_name.replace(" ", "_").replace("(", "").replace(")", "")
        self._active_tunnel = tunnel_name

        flog(f"WG connect: {conf_path} tunnel={tunnel_name}")
        try:
            result = subprocess.run([WIREGUARD_EXE, "/installtunnelservice", conf_path],
                                   capture_output=True, timeout=15)
            flog(f"WG install rc={result.returncode}")
            if result.returncode != 0:
                flog(f"WG install error: {result.stderr}")
                return False
            time.sleep(3)
            return True
        except Exception as e:
            flog(f"WG connect error: {e}")
            return False

    def connect_vpn_proton(self):
        """Connect VPN via WireGuard (single account mode)"""
        country = self.vpn_country.get().strip()
        if not country:
            country = "United States"

        return self.connect_vpn_proton_country(country)

    def connect_vpn_proton_country(self, country):
        """Connect VPN to specific country via WireGuard — uses ALL configs for max IP diversity"""
        self.log(f"VPN → {country} (WireGuard)...")

        # Track used configs in this batch to never reuse same IP
        if not hasattr(self, '_used_vpn_configs'):
            self._used_vpn_configs = set()

        # Collect ALL .conf files (not just matching country) for maximum IP diversity
        all_confs = []
        country_confs = []
        if os.path.isdir(VPN_CONFIGS_DIR):
            code = COUNTRY_TO_CODE.get(country, country.upper()[:2])
            for f in os.listdir(VPN_CONFIGS_DIR):
                if not f.endswith(".conf"):
                    continue
                full = os.path.join(VPN_CONFIGS_DIR, f)
                if f not in self._used_vpn_configs:
                    all_confs.append(full)
                    if f"wg-{code}-" in f:
                        country_confs.append(full)

        # Prefer matching country, but use ANY if not available
        if country_confs:
            configs = country_confs
        elif all_confs:
            configs = all_confs
        else:
            # All 55 configs used — reset and start over
            self._used_vpn_configs.clear()
            self.log("All VPN configs used (55) — resetting...")
            all_confs = []
            if os.path.isdir(VPN_CONFIGS_DIR):
                for f in os.listdir(VPN_CONFIGS_DIR):
                    if f.endswith(".conf"):
                        all_confs.append(os.path.join(VPN_CONFIGS_DIR, f))
            if not all_confs:
                self.log("Hta config WireGuard mal9ach! Dir configs f vpn_configs/")
                return False
            configs = all_confs

        # Pick random config
        conf_path = random.choice(configs)
        conf_name = os.path.basename(conf_path)
        self._used_vpn_configs.add(conf_name)
        self._last_vpn_conf = conf_name
        self.log(f"Config: {os.path.basename(conf_path)}")

        # Get initial IP
        orig_ip, orig_cc, _ = self._check_vpn_ip()
        if orig_ip:
            self.log(f"IP daba: {orig_ip} | {orig_cc}")

        # Connect
        if not self._wg_connect(conf_path):
            self.log("WireGuard ma connectatch!")
            return False

        # Poll until IP changes — max 30 sec
        self.log("Kanchuf wach VPN connecti...")
        for i in range(6):
            if self._stop_flag:
                self.log("VPN polling stopped (STOP flag).")
                return False
            time.sleep(5)
            new_ip, new_cc, new_org = self._check_vpn_ip()
            if new_ip and orig_ip and new_ip != orig_ip:
                self.log(f"VPN CONNECTI! IP: {new_ip} | Country: {new_cc} | {new_org}")
                # Wait extra for routing to stabilize
                time.sleep(5)
                return True
            self.log(f"  Tsana VPN... ({(i+1)*5}s)")

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
        """Kill Chrome, disconnect VPN, re-enable buttons, clear log"""
        self._stop_flag = True
        self._skip_flag = True
        self._batch_mode = False
        self._batch_remaining = None
        self._kill_bot_chrome()
        try:
            self._wg_disconnect()
        except Exception:
            pass

        self.batch_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
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

    def _get_sheet_id(self):
        """Extract Google Sheet ID from URL"""
        source = self.csv_path_var.get().strip()
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', source)
        if match:
            sid = match.group(1)
            # Skip if it's /d/e/ (published key, not real ID)
            if '/d/e/' in source:
                return None
            return sid
        return None

    def _load_csv_data(self):
        """Load accounts from CSV file or Google Sheets URL"""
        source = self.csv_path_var.get().strip()
        if not source:
            messagebox.showerror("Erreur", "Dakhel Google Sheets URL wla CSV file path!")
            return []

        try:
            import csv, io
            if source.startswith("http") and "google.com" in source:
                # Google Sheets — use gspread if credentials exist
                sheet_id = self._get_sheet_id()
                creds_path = os.path.join(BASE_DIR, "credentials.json")
                if sheet_id and os.path.exists(creds_path):
                    self.log("Loading from Google Sheets (gspread)...")
                    import gspread
                    from google.oauth2.service_account import Credentials
                    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
                    gc = gspread.authorize(creds)
                    sh = gc.open_by_key(sheet_id)
                    ws = sh.sheet1
                    records = ws.get_all_records()
                    rows = [{k: str(v) for k, v in r.items()} for r in records]
                else:
                    # Fallback: published CSV URL
                    import urllib.request
                    self.log("Loading from Google Sheets (CSV)...")
                    req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        content = resp.read().decode("utf-8")
                    reader = csv.DictReader(io.StringIO(content))
                    rows = list(reader)
            elif source.startswith("http"):
                import urllib.request
                self.log("Loading from URL...")
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

            # Save all rows for filtering
            self._all_rows_unfiltered = rows
            # Apply current filter
            self._apply_filter()
            self.log(f"Loaded: {len(self.batch_rows)} accounts (total in sheet: {len(rows)})")
            return rows
        except Exception as e:
            messagebox.showerror("Error", f"Ma9dertch nqra l data:\n{e}")
            return []

    def _start_2fa_batch(self):
        """Load accounts with 'ok' status and run 2FA setup on them"""
        self.log("2FA BATCH: Loading accounts with 'ok' status...")
        source = self.csv_path_var.get().strip()
        if not source:
            messagebox.showerror("Erreur", "Dakhel Google Sheets URL wla CSV file path!")
            return
        try:
            import csv, io
            if source.startswith("http") and "google.com" in source:
                sheet_id = self._get_sheet_id()
                creds_path = os.path.join(BASE_DIR, "credentials.json")
                if sheet_id and os.path.exists(creds_path):
                    import gspread
                    from google.oauth2.service_account import Credentials
                    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
                    gc = gspread.authorize(creds)
                    sh = gc.open_by_key(sheet_id)
                    ws = sh.sheet1
                    records = ws.get_all_records()
                    rows = [{k: str(v) for k, v in r.items()} for r in records]
                else:
                    self.log("Credentials not found!")
                    return
            else:
                with open(source, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)

            # Filter: only "ok" status (created but no 2FA)
            ok_rows = [r for r in rows if r.get("status", "").strip().lower() in ("ok", "2fa_fail")]
            if not ok_rows:
                self.log("2FA BATCH: No accounts needing 2FA found!")
                messagebox.showinfo("2FA", "No accounts with 'ok' or '2fa_fail' status to process.")
                return

            self.batch_rows = ok_rows
            self._populate_table()
            self.log(f"2FA BATCH: {len(ok_rows)} accounts to setup 2FA")

            self._stop_flag = False
            self._skip_flag = False
            self.batch_btn.configure(state="disabled")
            self.twofa_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.next_btn.configure(state="normal")
            thread = threading.Thread(target=self._run_2fa_batch)
            thread.daemon = True
            thread.start()
        except Exception as e:
            self.log(f"2FA BATCH Error: {e}")

    def _run_2fa_batch(self):
        """Run 2FA setup for all 'ok' accounts"""
        try:
            self._batch_mode = True
            total = len(self.batch_rows)
            results = {"ok": [], "fail": []}
            for step, row in enumerate(self.batch_rows):
                if self._stop_flag:
                    self.log(f"2FA BATCH STOPPED. {total - step} remaining.")
                    break
                self._skip_flag = False

                email = row.get("email", "").strip()
                out_pass = row.get("password", row.get("pass", "")).strip()
                if not email or not out_pass:
                    self.log(f"2FA SKIP: missing email/password")
                    continue

                self.log(f"\n{'='*40}")
                self.log(f"2FA ACCOUNT {step+1}/{total}: {email}")
                self.log(f"{'='*40}")
                self._update_table_status(step, "running")
                self.update_status(f"2FA: {step+1}/{total}", "orange")

                self._2fa_totp_secret = None
                try:
                    asyncio.run(run_2fa_only(self, email, out_pass))

                    if self._2fa_totp_secret:
                        results["ok"].append(email)
                        self._update_table_status(step, "ok+2fa")
                        self._update_sheet_status(email, "ok+2fa")
                        self._update_sheet_totp(email, self._2fa_totp_secret)
                        self.log(f"2FA OK: {email}")
                    else:
                        results["fail"].append(email)
                        self._update_table_status(step, "2fa_fail")
                        self._update_sheet_status(email, "2fa_fail")
                        self.log(f"2FA FAIL: {email}")
                except Exception as e:
                    flog(f"2FA BATCH EXCEPTION: {e}")
                    results["fail"].append(email)
                    self._update_table_status(step, "2fa_fail")
                    self._update_sheet_status(email, "2fa_fail")

                if step < total - 1 and not self._stop_flag:
                    self.log("Pause 3 sec...")
                    for _ in range(3):
                        if self._stop_flag:
                            break
                        time.sleep(1)

            self.log(f"\n{'='*40}")
            self.log(f"2FA BATCH FINISHED! OK: {len(results['ok'])} | FAIL: {len(results['fail'])}")
        finally:
            self._batch_mode = False
            self.root.after(0, lambda: self.batch_btn.configure(state="normal"))
            self.root.after(0, lambda: self.twofa_btn.configure(state="normal"))
            self.root.after(0, lambda: self.stop_btn.configure(state="disabled"))
            self.root.after(0, lambda: self.next_btn.configure(state="disabled"))

    def _retry_failed(self):
        """Reload from sheets, filter non-ok accounts, and start batch"""
        self.log("RETRY: Reloading from sheets (non-ok accounts only)...")
        rows = self._load_csv_data()
        if rows and self.batch_rows:
            self.log(f"RETRY: {len(self.batch_rows)} accounts to retry")
            self.start_batch()
        else:
            self.log("RETRY: No accounts to retry — all OK!")

    def _import_accounts(self):
        """Import accounts from CSV/Sheets into table without running batch"""
        rows = self._load_csv_data()
        if rows:
            self.log(f"Imported {len(rows)} accounts. Select li bghiti o click BATCH.")

    def start_batch(self):
        flog(f"=== start_batch called. batch_rows={len(getattr(self, 'batch_rows', []))}, btn_state={self.batch_btn.cget('state')} ===")
        # If data not loaded yet, load it
        if not hasattr(self, 'batch_rows') or not self.batch_rows:
            rows = self._load_csv_data()
            if not rows:
                return

        # Resume from where we stopped, or build new list
        if hasattr(self, '_batch_remaining') and self._batch_remaining:
            self._batch_indices = self._batch_remaining
            self._batch_remaining = None
            self.log(f"BATCH RESUME: {len(self._batch_indices)} accounts remaining")
        elif self._checked_rows:
            # 1 selected → start from that row to the end
            # multiple selected → only those rows
            if len(self._checked_rows) == 1:
                start_idx = min(self._checked_rows)
                self._batch_indices = list(range(start_idx, len(self.batch_rows)))
                self.log(f"BATCH: Starting from account {start_idx+1} → {len(self._batch_indices)} accounts")
            else:
                self._batch_indices = sorted(self._checked_rows)
                self.log(f"BATCH: {len(self._batch_indices)} selected accounts")
        else:
            self._batch_indices = list(range(len(self.batch_rows)))
            self.log(f"BATCH: All {len(self._batch_indices)} accounts (none selected)")

        self._stop_flag = False
        self._skip_flag = False
        self._used_vpn_configs = set()

        self.batch_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.next_btn.configure(state="normal")
        thread = threading.Thread(target=self._run_batch)
        thread.daemon = True
        thread.start()

    def _run_batch(self):
      try:
        self._batch_mode = True
        indices = self._batch_indices
        total = len(indices)
        results = {"ok": [], "skip": [], "fail": []}
        for step, idx in enumerate(indices):
            row = self.batch_rows[idx]
            if self._stop_flag:
                # Save remaining accounts so BATCH can resume
                self._batch_remaining = indices[step:]
                self.log(f"BATCH STOPPED by user. {len(self._batch_remaining)} accounts remaining — click BATCH to resume.")
                break

            # Reset skip flag for this account
            self._skip_flag = False

            self.log(f"\n{'='*40}")
            self.log(f"ACCOUNT {step+1}/{total}")
            self.log(f"{'='*40}")
            self.root.after(0, lambda s=step, t=total: self.batch_progress_var.set(f"Account {s+1}/{t}"))
            self._update_table_status(idx, "running")
            self.update_status(f"Batch: {step+1}/{total} | OK:{len(results['ok'])} SKIP:{len(results['skip'])} FAIL:{len(results['fail'])}", "orange")

            # Read fields from CSV row
            prenom = row.get("prenom", row.get("first_name", "")).strip()
            nom = row.get("nom", row.get("last_name", "")).strip()
            email = row.get("email", "").strip()
            out_pass = row.get("password", row.get("pass", "")).strip()

            if not prenom or not nom or not email or not out_pass:
                self.log(f"SKIP: missing prenom/nom/email/password")
                self._update_table_status(idx, "skip")
                results["skip"].append(email or f"row_{idx}")
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
            self._2fa_totp_secret = None
            try:
                # Connect VPN to account's country (retry with different config if fails)
                vpn_ok = self.connect_vpn_proton_country(account_country)
                if not vpn_ok:
                    self.log(f"VPN {account_country} failed — trying another country...")
                    vpn_ok = self.connect_vpn_proton_country(account_country)
                if not vpn_ok:
                    self.log(f"VPN still not connected — SKIP {email}")
                    results["skip"].append(email)
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "vpn_fail")
                    continue
                # Run the flow
                flog(f"=== LAUNCHING asyncio.run for {email} ===")
                asyncio.run(run_playwright_flow(self, prenom, nom, email, out_pass, dev_info or {}))
                flog(f"=== asyncio.run FINISHED for {email} ===")
                if self._skip_flag:
                    results["skip"].append(email)
                    self.log(f"SKIPPED (NEXT): {email}")
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "skip")
                elif self._last_result == "SKIP_CAPTCHA":
                    results["skip"].append(email)
                    self.log(f"CAPTCHA: {email}")
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "captcha")
                elif self._last_result == "SKIP_EXISTS":
                    results["skip"].append(email)
                    self.log(f"ALREADY CREATED: {email}")
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "already created")
                elif self._last_result == "SKIP_VERIFICATION":
                    results["skip"].append(email)
                    self.log(f"VERIFICATION: {email}")
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "verification")
                elif self._last_result == "phone":
                    results["skip"].append(email)
                    self.log(f"PHONE ASKED → SKIP: {email}")
                    self._update_table_status(idx, "phone")
                    self._update_sheet_status(email, "phone")
                else:
                    results["ok"].append(email)
                    totp_secret = getattr(self, '_2fa_totp_secret', None)
                    if totp_secret:
                        self.log(f"OK + 2FA: {email} | TOTP: {totp_secret[:4]}...{totp_secret[-4:]}")
                        self._update_table_status(idx, "ok+2fa")
                        self._update_sheet_status(email, "ok+2fa")
                        # Save TOTP synchronously (not background) to avoid VPN disconnect cutting connection
                        self._update_sheet_totp_sync(email, totp_secret)
                    else:
                        self.log(f"OK (no 2FA): {email}")
                        self._update_table_status(idx, "ok")
                        self._update_sheet_status(email, "ok")
            except Exception as e:
                flog(f"=== BATCH EXCEPTION for {email}: {type(e).__name__}: {e} ===")
                # Check _last_result first — it may have been set before the exception
                if self._last_result == "SKIP_CAPTCHA":
                    results["skip"].append(email)
                    self.log(f"CAPTCHA: {email}")
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "captcha")
                elif self._last_result == "SKIP_EXISTS":
                    results["skip"].append(email)
                    self.log(f"ALREADY CREATED: {email}")
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "already created")
                elif self._last_result == "SKIP_VERIFICATION":
                    results["skip"].append(email)
                    self.log(f"VERIFICATION: {email}")
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "verification")
                elif self._last_result == "phone":
                    results["skip"].append(email)
                    self.log(f"PHONE ASKED → SKIP: {email}")
                    self._update_table_status(idx, "phone")
                    self._update_sheet_status(email, "phone")
                elif self._skip_flag:
                    results["skip"].append(email)
                    self.log(f"SKIPPED (NEXT): {email}")
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "skip")
                elif "TargetClosedError" in type(e).__name__ or "closed" in str(e).lower():
                    self.log("Chrome tsad - normal.")
                    results["skip"].append(email)
                    self._update_table_status(idx, "skip")
                    self._update_sheet_status(email, "skip")
                else:
                    self.log(f"FAIL: {email} - {e}")
                    results["fail"].append(email)
                    self._update_table_status(idx, "fail")
                    self._update_sheet_status(email, "fail")

            # Remove processed account from table (not from sheets)
            self._remove_table_row(idx)

            flog(f"=== ACCOUNT DONE: {email} | moving to next... ===")
            flog(f"=== Results: skip_flag={self._skip_flag}, stop_flag={self._stop_flag}, last_result={self._last_result} ===")
            self.log(f"Account {step+1}/{total} | OK:{len(results['ok'])} SKIP:{len(results['skip'])} FAIL:{len(results['fail'])}")

            # Short pause between accounts
            if step < total - 1 and not self._stop_flag:
                self.log("Pause 5 sec before next account...")
                flog("=== PAUSE 5s ===")
                for _ in range(5):
                    if self._stop_flag or self._skip_flag:
                        break
                    time.sleep(1)
                flog("=== PAUSE DONE ===")

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
        self._batch_mode = False
        self._wg_disconnect()
        self.log("VPN disconnected (batch finished).")
        self.root.after(0, lambda: self.batch_btn.configure(state="normal"))
        self.root.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.root.after(0, lambda: self.next_btn.configure(state="disabled"))
      except Exception as batch_err:
        import traceback
        flog(f"=== BATCH THREAD CRASHED: {batch_err} ===")
        flog(traceback.format_exc())
        self._batch_mode = False
        self._wg_disconnect()
        self.root.after(0, lambda: self.batch_btn.configure(state="normal"))
        self.root.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.root.after(0, lambda: self.next_btn.configure(state="disabled"))

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

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)

    def _on_close():
        try:
            app._wg_disconnect()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()
