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
def download_gs_not_finished():

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get("https://scjg.gansu.gov.cn/guestweb4/s?siteCode=6200000052&checkHandle=1&pageSize=10&"
               "left_right_index=0&searchWord=%E4%BF%9D%E5%81%A5%E9%A3%9F%E5%93%81%E5%A4%87%E6%A1%88")

    time.sleep(5)
    driver.implicitly_wait(10)


    pages = []
    title_contains = "国产保健食品备案信息公示"

    # 使用XPath语法查找所有a标签，其中title属性包含指定内容
    xpath_expression = "//a[contains(normalize-space(.), '保健食品信息备案公示')]/@href"
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

    dic_path = '../../../Ingredient_Search/data_gs'
    print(hrefs)
    # for href in hrefs:
    #     file_path = os.path.join(dic_path, href.split('/')[-1]+'.pdf')
    #     download_link = href
    #     print("当前下载链接:", download_link)
    #     file_download(dic_path, download_link, file_path)
    #
    # import json
    # list_path = dic_path + '/hrefs.json'
    # with open(list_path, 'w', encoding='utf-8') as file:
    #     json.dump(pages, file, ensure_ascii=False, indent=4)  # 使用 ensure_ascii=False 保持中文字符

    # driver.quit()
    driver.quit()

if __name__ == '__main__':
    download_gs()