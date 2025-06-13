import time

import os
import requests
from selenium.webdriver.common.by import By
import re
from tqdm import tqdm
from selenium_chrome import get_chrome_driver
from file_download import file_download

def download_shanxi2(url='https://snamr.shaanxi.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'zcwj/gsgg.htm'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)

    time.sleep(1)
    # 提取页数


    hrefs = []
    for i in range(100):
        try:
            elements = driver.find_elements(By.XPATH, '//a[contains(text(), "保健食品备案凭证")]')
            # 提取 href 属性
            for element in elements:
                hrefs.append(element.get_attribute('href'))
        except Exception as e:
            continue
        #print(pages)
        #print("当前页数:", i+1)
        try:
            # 找到下一页按钮并点击
            next_page_button = driver.find_element(By.XPATH, '//span[@class="p_next p_fun"]/a')
            next_page_button.click()
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    time.sleep(3)  # 等待最多10秒
    dic_path = '../../../Ingredient_Search/data_shanxi2'
    for href in hrefs:
        time.sleep(1)
        file_path = os.path.join(dic_path, href.replace('.htm', '.html').split('/')[-1])
        download_link = href
        print("当前下载链接:", download_link)
        file_download(dic_path, download_link, file_path)

    import json
    list_path = '../../../Ingredient_Search/data_shanxi2/hrefs.json'
    with open(list_path, 'w', encoding='utf-8') as file:
        json.dump(hrefs, file, ensure_ascii=False, indent=4)  # 使用 ensure_ascii=False 保持中文字符

    # driver.quit()
    driver.quit()
