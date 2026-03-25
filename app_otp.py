import time
import re
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # Adding arguments to make the bot look more like a real user
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    # Maximize window to ensure elements are visible and not hidden by responsive design
    driver.maximize_window()
    return driver

def slow_type(element, text):
    """Types text slowly to mimic human behavior and avoid basic bot detection."""
    for char in text:
        element.send_keys(char)
        time.sleep(0.1)

def run_app():
    print("="*50)
    print("   🚀 APPLICATION: OUTLOOK AMAZON OTP EXTRACTOR 🚀")
    print("="*50)
    
    # You can change these or ask the user for input
    email = input("\n[1] Dakhel l'Email (Enter Email): ").strip()
    if not email:
        email = "SeymourWrobbel1284@hotmail.com" # Default fallback
        print(f"[*] Sta3melna l'email par défaut: {email}")
        
    password = input("[2] Dakhel l'Mot de passe (Enter Password): ").strip()
    if not password:
        password = "OFsd6cn2g0QXY7AL" # Default fallback
        print("[*] Sta3melna l'mot de passe par défaut.")

    print("\n[*] Kanbdaw l'application daba, mat9iyess walo (Don't touch anything)...")
    
    driver = create_driver()
    wait = WebDriverWait(driver, 20)
    
    try:
        # 1. Login to Outlook
        print("[*] Kanft7o page dyal login (Opening login page)...")
        driver.get('https://login.live.com/')
        
        print("[*] Kanktbou l'email...")
        email_input = wait.until(EC.element_to_be_clickable((By.NAME, 'loginfmt')))
        email_input.clear()
        slow_type(email_input, email)
        email_input.send_keys(Keys.RETURN)
        
        print("[*] Kantsnaw l'mot de passe...")
        time.sleep(3) # Wait for animation
        password_input = wait.until(EC.element_to_be_clickable((By.NAME, 'passwd')))
        password_input.clear()
        slow_type(password_input, password)
        password_input.send_keys(Keys.RETURN)
        
        # 2. Stay logged in prompt
        print("[*] Kandiro 'No' f stay signed in...")
        try:
            no_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'idBtn_Back')))
            no_button.click()
        except:
            pass # Sometimes it doesn't appear
            
        # 3. Open Outlook Inbox
        print("[+] Dkhelna l'compte b najah! Kanft7o l'Outlook Inbox...")
        driver.get('https://outlook.live.com/mail/0/')
        
        # Wait until the page loads completely (look for the navigation/folder list)
        print("[*] Kantsnaw les messages ybano...")
        time.sleep(8) 
        
        # 4. Search for Amazon OTP emails
        print("[*] Kan9elbo 3la les messages dyal 'Amazon'...")
        # Type Amazon in search bar
        search_box = wait.until(EC.element_to_be_clickable((By.ID, 'topSearchInput')))
        search_box.clear()
        search_box.send_keys("Amazon")
        search_box.send_keys(Keys.RETURN)
        
        print("[*] Kantsnaw resultats dyal recherche...")
        time.sleep(5)
        
        # 5. Extract the OTP from the page content
        # An easy way to find the OTP is to extract all text from the body and look for 6 digits
        # Especially since Outlook preview shows the text. We will click the first email just in case.
        
        try:
            # Click the first message in the list
            print("[*] Kanft7o awel message dyal Amazon...")
            # finding typical message item in outlook
            message_elements = driver.find_elements(By.CSS_SELECTOR, "[aria-label*='Amazon']")
            if message_elements:
                message_elements[0].click()
            else:
                # Fallback: Just click the center of the list or press Tab+Enter
                webdriver.ActionChains(driver).send_keys(Keys.TAB).send_keys(Keys.ENTER).perform()
        except Exception as e:
            print(f"[-] Mal9inach l'message bdbt: {e}")
            
        time.sleep(4) # Let the email reading pane load
        
        page_text = driver.find_element(By.TAG_NAME, 'body').text
        
        # Extract OTP (usually 6 digits)
        print("[*] Kanjangdbu l'OTP (Extracting OTP)...")
        # Regex to find exactly 6 digits not surrounded by other digits
        otp_matches = re.findall(r'\b\d{6}\b', page_text)
        
        if otp_matches:
            # Take the first one, which is likely the OTP in the email body
            otp_code = otp_matches[0]
            print(f"[+] L9ina l'OTP: {otp_code}")
            
            # 6. Save to otp.txt
            with open('otp.txt', 'w') as f:
                f.write(otp_code)
            print("[+] L'OTP tsajel mzyan f fichier 'otp.txt'.")
            
        else:
            print("[-] Mal9inach hta OTP f l'email dyal Amazon.")
            
    except Exception as e:
        print(f"[-] Erreur wa9e3 f l'application: {e}")
        print("[*] Momkin Microsoft blockat l'login wella connexion t9ila.")
    
    finally:
        print("\n[*] L'application salat. L'Navigateur ghadi yb9a mehloul 1 mn bach tchouf b 3inik.")
        time.sleep(60)
        driver.quit()

if __name__ == "__main__":
    run_app()
