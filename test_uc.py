import time
try:
    import undetected_chromedriver as uc
except ImportError:
    print("undetected_chromedriver not installed")
    exit(1)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

email = "SeymourWrobbel1284@hotmail.com"
password = "OFsd6cn2g0QXY7AL"

if __name__ == '__main__':
    print("Testing undetected_chromedriver...")
    options = uc.ChromeOptions()
    # options.add_argument('--headless') # let's run non-headless to avoid immediate blocks first
    driver = uc.Chrome(options=options)
    try:
        driver.get('https://login.live.com/')
        wait = WebDriverWait(driver, 15)
        
        print("Entering email...")
        email_input = wait.until(EC.element_to_be_clickable((By.NAME, 'loginfmt')))
        email_input.send_keys(email)
        
        next_button = wait.until(EC.element_to_be_clickable((By.ID, 'idSIButton9')))
        next_button.click()
        
        time.sleep(3)
        print("Waiting for password field...")
        password_input = wait.until(EC.element_to_be_clickable((By.NAME, 'passwd')))
        
        print("SUCCESS: Reached password field!")
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        driver.quit()
