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
def download_cq(url="https://scjgj.cq.gov.cn/"):
    if not url.endswith('/'):
        url += '/'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url+"cqs/searchResultPC.html?tenantId=70&configTenantId=70&areaCode=500000137&searchWord=%E5%9B%BD%E4%BA%A7%E4%BF%9D%E5%81%A5%E9%A3%9F%E5%93%81%E5%A4%87%E6%A1%88%E4%BF%A1%E6%81%AF%E5%85%AC%E7%A4%BA")

    time.sleep(5)
    driver.implicitly_wait(10)


    pages = []
    title_contains = "国产保健食品备案信息公示"

    # 使用XPath语法查找所有a标签，其中title属性包含指定内容
    xpath_expression = f"//a[contains(@title, '{title_contains}')]"
    elements = driver.find_elements(By.XPATH, xpath_expression)

    # 遍历找到的a标签，提取href
    for element in elements:
        href = element.get_attribute('href')
        pages.append(href)


    time.sleep(3)  # 等待最多10秒
    hrefs = []

    for page in pages:
        driver.get(page)
        elements = driver.find_elements(By.XPATH, '//a[contains(text(), ".pdf")]')

        # 提取 href 属性
        for element in elements:
            href = element.get_attribute('href')
            hrefs.append(href)

    dic_path = '../../../Ingredient_Search/data_cq'

    for href in hrefs:
        file_path = os.path.join(dic_path, href.split('/')[-1]+'.pdf')
        download_link = href
        print("当前下载链接:", download_link)
        file_download(dic_path, download_link, file_path)

    import json
    list_path = dic_path + '/hrefs.json'
    with open(list_path, 'w', encoding='utf-8') as file:
        json.dump(pages, file, ensure_ascii=False, indent=4)  # 使用 ensure_ascii=False 保持中文字符

    # driver.quit()
    driver.quit()
