import time

import os
import requests
from selenium.webdriver.common.by import By
import re
from tqdm import tqdm
from selenium_chrome import get_chrome_driver
from file_download import file_download
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
def download_sh(url='https://scjgj.sh.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += '940/index.html'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)

    time.sleep(1)
    # 提取页数



    pages = []
    for i in range(10):
        try:
            elements = driver.find_elements(By.XPATH,
                                               "//a[contains(@title, '保健食品备案信息公示')]")

            # 提取 href 属性
            for element in elements:
                pages.append(element.get_attribute('href'))
        except Exception as e:
            continue
        #print(pages)
        #print("当前页数:", i+1)
        try:
            # 找到下一页按钮并点击
            next_page_button = driver.find_element(By.XPATH, "//div[contains(text(), '下一页')]")
            next_page_button.click()
        except Exception as e:
            print(f"An error occurred: {e}")

            break
    print(pages)
    time.sleep(3)  # 等待最多10秒
    hrefs = []

    for page in pages:
        driver.get(page)
        elements = driver.find_elements(By.XPATH, '//a[contains(@href, ".pdf")]')

        # 提取 href 属性
        for element in elements:
            href = element.get_attribute('href')
            hrefs.append(href)

    print(hrefs)
    dic_path = '../../../Ingredient_Search/data_sh'

    import json

    list_path = dic_path + '/hrefs.json'
    with open(list_path, 'w', encoding='utf-8') as file:
        json.dump(hrefs, file, ensure_ascii=False, indent=4)  # 使用 ensure_ascii=False 保持中文字符
    for href in hrefs:
        file_path = os.path.join(dic_path, href.split('/')[-1]+'.pdf')
        download_link = href
        print("当前下载链接:", download_link)
        file_download(dic_path, download_link, file_path)



    # driver.quit()
    driver.quit()
