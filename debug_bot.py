import time
from selenium import webdriver

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(options=options)
driver.get('https://login.live.com/')
time.sleep(5)
driver.save_screenshot('screenshot.png')
with open('page_source.html', 'w', encoding='utf-8') as f:
    f.write(driver.page_source)
driver.quit()
print("Debug info saved.")
