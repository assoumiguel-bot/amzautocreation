"""
Amazon Developer Bot - Bou7do (sans VPN).
Tab 1 = Amazon/login.live.com (jamais remplacer)
Tab 2 = Outlook (uniquement quand OTP demande)
Croix = fermer Chrome manuellement
"""
import time
import re
import os

try:
    import undetected_chromedriver as uc
    driver = uc.Chrome()
except Exception:
    from selenium import webdriver
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SMIYA = "Fatiha salam"
EMAIL = "ChrysantaTatel6980@hotmail.com"
PASSWORD = "NNoGMPRN85t"

def fast_type(el, text):
    el.send_keys(text)

def log(msg):
    print(f"[*] {msg}")

wait = WebDriverWait(driver, 25)
wait_long = WebDriverWait(driver, 15)
driver.maximize_window()

# ========== TAB 1 UNIQUEMENT - Amazon / login.live.com ==========
# On ne quitte JAMAIS cette tab pour aller sur Outlook ici.

log("MAR7ALA 1: Opening Amazon Developer...")
driver.get("https://developer.amazon.com/")
time.sleep(5)

log("MAR7ALA 2: Clicking Sign In...")
for sel in ["a.devportal-signin", "a[href*='signin']", "a[href*='login']"]:
    try:
        btn = driver.find_element(By.CSS_SELECTOR, sel)
        if btn.is_displayed():
            btn.click()
            log(f"   Clicked: {sel}")
            break
    except Exception:
        pass
time.sleep(5)

url = driver.current_url
if "login.live.com" not in url and "microsoftonline" not in url and "amazon.com/ap" not in url:
    log("MAR7ALA 3a: Redirecting to login.live.com...")
    driver.get("https://login.live.com/")
    time.sleep(5)

log("MAR7ALA 4: Typing email in Tab 1 (Amazon/Login)...")
em = None
for s in [(By.ID, 'i0116'), (By.NAME, 'loginfmt'), (By.CSS_SELECTOR, "input[type='email']"),
          (By.CSS_SELECTOR, "input[type='text']"), (By.ID, 'ap_email'), (By.NAME, 'email')]:
    try:
        driver.switch_to.default_content()
        em = wait_long.until(EC.element_to_be_clickable(s))
        if em and em.is_displayed():
            break
    except Exception:
        continue
if not em:
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for ifr in iframes:
            try:
                driver.switch_to.frame(ifr)
                em = driver.find_element(By.ID, "i0116")
                if em and em.is_displayed():
                    log("   Switched to login iframe.")
                    break
            except Exception:
                driver.switch_to.default_content()
        else:
            driver.switch_to.default_content()
    except Exception:
        driver.switch_to.default_content()
if not em:
    raise Exception("Mal9inach email field f Tab 1.")
em.click()
time.sleep(0.5)
em.clear()
fast_type(em, EMAIL)
time.sleep(0.5)
try:
    driver.find_element(By.ID, 'idSIButton9').click()
except Exception:
    try:
        driver.find_element(By.ID, 'continue').click()
    except Exception:
        em.send_keys(Keys.RETURN)
log("   Email sent.")
time.sleep(5)

log("MAR7ALA 5: Typing password in Tab 1...")
try:
    driver.switch_to.default_content()
except Exception:
    pass
pw = None
for s in [(By.ID, 'i0118'), (By.NAME, 'passwd'), (By.ID, 'ap_password')]:
    try:
        pw = wait_long.until(EC.element_to_be_clickable(s))
        if pw and pw.is_displayed():
            break
    except Exception:
        continue
if not pw:
    raise Exception("Mal9inach password field f Tab 1.")
pw.click()
time.sleep(0.3)
pw.clear()
fast_type(pw, PASSWORD)
time.sleep(0.5)
try:
    driver.find_element(By.ID, 'idSIButton9').click()
except Exception:
    try:
        driver.find_element(By.ID, 'signInSubmit').click()
    except Exception:
        pw.send_keys(Keys.RETURN)
log("   Password sent.")
time.sleep(3)
try:
    driver.find_element(By.ID, 'idBtn_Back').click()
    log("   Stay signed in: No.")
except Exception:
    pass
time.sleep(3)

# ========== Attendre OTP (15-20s) - rester sur Tab 1 ==========
log("MAR7ALA 6: Waiting for OTP field on Tab 1 (15-20 sec)...")
otp_input = None
for attempt in range(20):
    try:
        driver.switch_to.default_content()
        for sel in [(By.ID, "idTxtBx_SAOTCC_OTC"), (By.NAME, "otc"),
                    (By.CSS_SELECTOR, "input[type='tel']"),
                    (By.CSS_SELECTOR, "input[autocomplete='one-time-code']")]:
            try:
                el = driver.find_elements(sel[0], sel[1])
                for e in el:
                    if e.is_displayed() and e.tag_name.lower() == "input":
                        otp_input = e
                        break
                if otp_input:
                    break
            except Exception:
                pass
        if otp_input:
            log(f"   OTP field found after {attempt + 1}s.")
            break
    except Exception:
        pass
    time.sleep(1)

if not otp_input:
    log("MAR7ALA 7: No OTP needed - already logged in!")
    log("[+] Done. Tab 1 = Amazon. Close Chrome with X when you want.")
    while True:
        time.sleep(60)
    # Pas de driver.quit() - user ferme manuellement

# ========== OTP demande -> Ouvrir TAB 2 pour Outlook UNIQUEMENT ==========
log("MAR7ALA 8: OTP requested. Opening Tab 2 for Outlook...")
driver.execute_script("window.open('');")
driver.switch_to.window(driver.window_handles[-1])
log("   Tab 2 = Outlook (new tab)")

log("MAR7ALA 9: Tab 2 - Login Outlook...")
driver.get('https://login.live.com/')
time.sleep(4)

em2 = wait_long.until(EC.element_to_be_clickable((By.ID, 'i0116')))
em2.clear()
fast_type(em2, EMAIL)
driver.find_element(By.ID, 'idSIButton9').click()
time.sleep(4)

pw2 = wait_long.until(EC.element_to_be_clickable((By.ID, 'i0118')))
pw2.clear()
fast_type(pw2, PASSWORD)
driver.find_element(By.ID, 'idSIButton9').click()
time.sleep(3)
try:
    driver.find_element(By.ID, 'idBtn_Back').click()
except Exception:
    pass
time.sleep(2)

log("MAR7ALA 10: Tab 2 - Opening Outlook inbox...")
driver.get('https://outlook.live.com/mail/0/')
time.sleep(10)

log("MAR7ALA 11: Tab 2 - Searching Amazon emails...")
search = wait.until(EC.element_to_be_clickable((By.ID, 'topSearchInput')))
search.click()
fast_type(search, "Amazon")
search.send_keys(Keys.RETURN)
time.sleep(6)

log("MAR7ALA 12: Tab 2 - Extracting OTP...")
body = driver.find_element(By.TAG_NAME, 'body').text
otp_matches = re.findall(r'\b\d{6}\b', body)
if not otp_matches:
    otp_matches = re.findall(r'\b\d{4,8}\b', body)
if not otp_matches:
    log("[-] Mal9inach OTP f Outlook.")
else:
    otp = otp_matches[0]
    log(f"   OTP = {otp}")
    with open(os.path.join(BASE_DIR, 'otp.txt'), 'w') as f:
        f.write(otp)

    log("MAR7ALA 13: Back to Tab 1 - Pasting OTP...")
    driver.switch_to.window(driver.window_handles[0])
    time.sleep(2)

    otp_input = None
    for sel in [(By.ID, "idTxtBx_SAOTCC_OTC"), (By.NAME, "otc")]:
        try:
            el = driver.find_elements(sel[0], sel[1])
            for e in el:
                if e.is_displayed():
                    otp_input = e
                    break
            if otp_input:
                break
        except Exception:
            pass
    if not otp_input:
        for sel in [(By.CSS_SELECTOR, "input[type='tel']"), (By.CSS_SELECTOR, "input[autocomplete='one-time-code']")]:
            try:
                el = driver.find_elements(sel[0], sel[1])
                for e in el:
                    if e.is_displayed():
                        otp_input = e
                        break
            except Exception:
                pass

    if otp_input:
        otp_input.clear()
        fast_type(otp_input, otp)
        time.sleep(0.5)
        try:
            driver.find_element(By.ID, "idSubmit_SAOTCC_Continue").click()
        except Exception:
            try:
                driver.find_element(By.ID, "idSIButton9").click()
            except Exception:
                otp_input.send_keys(Keys.RETURN)
        log("[+] OTP pasted in Tab 1!")
    else:
        log(f"[!] OTP = {otp} - paste manually in Tab 1.")

log("[+] Done. Tab 1 = Amazon. Close Chrome with X (croix) when you want.")
while True:
    time.sleep(60)
# Pas de driver.quit() - l'utilisateur ferme manuellement
