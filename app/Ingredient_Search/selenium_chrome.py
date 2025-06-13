from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def get_chrome_driver():
    chrome_driver_path = r"../../../Ingredient_Search/chromedriver-win64/chromedriver.exe"
    options = Options()

    options.add_argument("--incognito")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36")
    service = Service(chrome_driver_path)
    chrome_driver = webdriver.Chrome(service=service, options=options)

    return chrome_driver