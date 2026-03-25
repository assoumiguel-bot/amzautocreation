import os
import re
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure your details here (Leave blank to be prompted when running)
SMIYA = "" 
EMAIL = ""
PASSWORD = ""

def get_config():
    global SMIYA, EMAIL, PASSWORD
    if not SMIYA:
        SMIYA = input("[1] Name (Prenom + Nom): ").strip()
    if not EMAIL:
        EMAIL = input("[2] Outlook Email: ").strip()
    if not PASSWORD:
        PASSWORD = input("[3] Outlook Password: ").strip()

    if not SMIYA or not EMAIL or not PASSWORD:
        log("Error: Mission information. Using defaults from script backup if possible.")
        if not EMAIL: EMAIL = "ChrysantaTatel6980@hotmail.com"
        if not PASSWORD: PASSWORD = "NoGMPRN85t"
        if not SMIYA: SMIYA = "Fatiha salam"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def log(msg):
    print(f"[*] {msg}")

def human_type(el, text):
    """Types text with random delays to mimic human behavior."""
    for char in text:
        el.send_keys(char)
        time.sleep(random.uniform(0.1, 0.3))

def init_driver():
    log("Initializing undetectable Chrome...")
    options = uc.ChromeOptions()
    # Adding some common arguments to reduce detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)
    return driver

def solve_amazon_flow(driver):
    wait = WebDriverWait(driver, 20)
    
    log("Step 1: Navigating to Amazon Registration...")
    # Using a direct registration URL to minimize transitions
    reg_url = "https://www.amazon.com/ap/register?openid.return_to=https%3A%2F%2Fdeveloper.amazon.com%2Fdashboard&openid.assoc_handle=mas_dev_portal&openid.mode=checkid_setup&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
    driver.get(reg_url)
    time.sleep(random.uniform(3, 5))

    try:
        log("Step 2: Filling in user details...")
        name_field = wait.until(EC.visibility_of_element_located((By.ID, "ap_customer_name")))
        human_type(name_field, SMIYA)
        
        email_field = driver.find_element(By.ID, "ap_email")
        human_type(email_field, EMAIL)
        
        pass_field = driver.find_element(By.ID, "ap_password")
        human_type(pass_field, PASSWORD)
        
        pass_check = driver.find_element(By.ID, "ap_password_check")
        human_type(pass_check, PASSWORD)
        
        log("Submitting registration form...")
        driver.find_element(By.ID, "continue").click()
        
    except Exception as e:
        log(f"Error during form filling: {e}")
        return False

    log("Step 3: Waiting for OTP field or Captcha...")
    # Detect if OTP field appears or if we are blocked by Captcha
    otp_found = False
    for i in range(30):
        if "cvf" in driver.current_url or driver.find_elements(By.ID, "auth-mfa-otpcode") or driver.find_elements(By.NAME, "otc"):
            log("OTP field detected!")
            otp_found = True
            break
        if driver.find_elements(By.ID, "auth-captcha-image"):
            log("!!! CAPTCHA detected. Please solve it manually in the browser window.")
            # Wait for user to solve captcha or for the page to change
            while driver.find_elements(By.ID, "auth-captcha-image"):
                time.sleep(2)
            log("Captcha solved, continuing...")
            continue
        time.sleep(1)
    
    if not otp_found:
        log("Could not find OTP field after 30 seconds.")
        return False
    
    return True

def get_otp_from_outlook(driver):
    log("Step 4: Opening Outlook in a new tab...")
    driver.execute_script("window.open('https://login.live.com/', '_blank');")
    time.sleep(2)
    driver.switch_to.window(driver.window_handles[-1])
    
    wait = WebDriverWait(driver, 20)
    
    try:
        log("Logging into Outlook...")
        email_in = wait.until(EC.element_to_be_clickable((By.NAME, "loginfmt")))
        human_type(email_in, EMAIL)
        email_in.send_keys(Keys.RETURN)
        
        time.sleep(2)
        pass_in = wait.until(EC.element_to_be_clickable((By.NAME, "passwd")))
        human_type(pass_in, PASSWORD)
        pass_in.send_keys(Keys.RETURN)
        
        # Handle stay signed in
        try:
            no_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "idBtn_Back")))
            no_btn.click()
        except:
            pass
            
        log("Navigating to Inbox...")
        driver.get("https://outlook.live.com/mail/0/")
        time.sleep(8) # Wait for mail to load
        
        log("Searching for Amazon email...")
        search_box = wait.until(EC.element_to_be_clickable((By.ID, "topSearchInput")))
        search_box.click()
        human_type(search_box, "Amazon")
        search_box.send_keys(Keys.RETURN)
        time.sleep(5)
        
        log("Extracting OTP...")
        # Get body text and search for 6 digits
        body_text = driver.find_element(By.TAG_NAME, "body").text
        otp_matches = re.findall(r'\b\d{6}\b', body_text)
        
        if not otp_matches:
            log("OTP not found in body text, trying to click the first email...")
            try:
                first_mail = driver.find_element(By.CSS_SELECTOR, "[aria-label*='Amazon']")
                first_mail.click()
                time.sleep(3)
                body_text = driver.find_element(By.TAG_NAME, "body").text
                otp_matches = re.findall(r'\b\d{6}\b', body_text)
            except:
                pass

        if otp_matches:
            otp = otp_matches[0]
            log(f"Found OTP: {otp}")
            return otp
        else:
            log("Failed to find OTP in Outlook.")
            return None
            
    except Exception as e:
        log(f"Error in Outlook flow: {e}")
        return None
    finally:
        # Close Outlook tab and go back to Amazon
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

def main():
    get_config()
    driver = init_driver()
    try:
        if solve_amazon_flow(driver):
            otp = get_otp_from_outlook(driver)
            if otp:
                log("Pasting OTP into Amazon...")
                # Search for any common OTP input ID
                otp_field = None
                for selector in ["#cvf-input-code", "input[name='otc']", "input[type='tel']", "#auth-mfa-otpcode"]:
                    try:
                        otp_field = driver.find_element(By.CSS_SELECTOR, selector)
                        if otp_field.is_displayed():
                            break
                    except:
                        continue
                
                if otp_field:
                    human_type(otp_field, otp)
                    time.sleep(1)
                    try:
                        driver.find_element(By.ID, "cvf-submit-code").click()
                    except:
                        try:
                            driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
                        except:
                            otp_field.send_keys(Keys.RETURN)
                    log("OTP Submitted! Account creation should be finishing...")
                else:
                    log(f"Could't find the OTP input field on Amazon. Manual entry required: {otp}")
        else:
            log("Amazon flow interrupted or failed.")
            
    finally:
        log("Automation finished. Browser will remain open for inspection.")
        # Keeping browser open as requested implicitly by "KAMAL 3LA PROJECT"
        while True:
            time.sleep(10)

if __name__ == "__main__":
    main()
