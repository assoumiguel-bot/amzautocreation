import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def login_to_outlook(email, password):
    print(f"[*] Starting bot for: {email}")
    
    # Setup Chrome options
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless') # Uncomment if you want it to run in the background
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Initialize driver
    driver = webdriver.Chrome(options=options)
    
    try:
        # Navigate to Outlook login page
        driver.get('https://login.live.com/')
        
        wait = WebDriverWait(driver, 15)
        
        # 1. Enter Email
        print("[*] Entering email...")
        email_input = wait.until(EC.element_to_be_clickable((By.NAME, 'loginfmt')))
        email_input.clear()
        email_input.send_keys(email)
        
        # Click Next
        next_button = wait.until(EC.element_to_be_clickable((By.ID, 'idSIButton9')))
        next_button.click()
        
        # 2. Enter Password
        print("[*] Entering password...")
        # Add a small delay to make it look more human
        time.sleep(2) 
        password_input = wait.until(EC.element_to_be_clickable((By.NAME, 'passwd')))
        password_input.clear()
        password_input.send_keys(password)
        
        # Click Sign In
        sign_in_button = wait.until(EC.element_to_be_clickable((By.ID, 'idSIButton9')))
        sign_in_button.click()
        
        # 3. Handle "Stay signed in?" prompt
        print("[*] Handling 'Stay signed in' prompt...")
        try:
            # Click "No" (or Yes depending on your preference)
            no_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'idBtn_Back')))
            no_button.click()
        except:
            print("[*] 'Stay signed in' prompt not found, continuing...")
        
        print("[+] Successfully logged in!")
        print("[*] You can now view your inbox. Leaving the browser open...")
        
        # Keep browser open to see the result
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"[-] An error occurred: {e}")
    finally:
        # driver.quit() # Uncomment to close browser automatically when done
        pass

if __name__ == "__main__":
    print("=== Outlook Login Bot ===")
    user_email = "SeymourWrobbel1284@hotmail.com"
    user_password = "OFsd6cn2g0QXY7AL"
    print(f"[*] Automating login for: {user_email}")
    
    login_to_outlook(user_email, user_password)
