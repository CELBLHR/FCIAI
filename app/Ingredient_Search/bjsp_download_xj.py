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

def download_xj(url='https://scjgj.xinjiang.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'guestweb5/html/searchResult.html?column=%25E5%2585%25A8%25E9%2583%25A8&uc=1&searchWord=%25E4%25BF%259D%25E5%2581%25A5%25E9%25A3%259F%25E5%2593%2581%25E5%25A4%2587%25E6%25A1%2588&siteCode=65BM060002'
    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)
    time.sleep(1)
    # 提取页数

    hrefs = []
    pages = []
    try:
        # 等待页面加载完成
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located
        )

        # 使用XPath定位包含特定文本的<a>元素
        # 注意：XPath表达式已根据提供的文本内容进行调整
        elements = driver.find_elements(By.XPATH,
                                        '//a[contains(@title, "保健食品备案公示")]')

        # 提取href属性
        for e in elements:
            pages.append(e.get_attribute('href'))


    except Exception as e:
        print(f'发生异常: {e}')
    pages = list(set(pages))
    print(pages)
    time.sleep(3)


    for page in pages:
        driver.get(page)
        WebDriverWait(driver, 3).until(
            EC.presence_of_all_elements_located
        )
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, '.zip')]")

        # 提取并打印href属性
        for link in pdf_links:
            href = link.get_attribute('href')
            hrefs.append(href)

    print(hrefs)

    dic_path = '../../../Ingredient_Search/data_xj'
    for href in hrefs:
        time.sleep(1)
        file_path = os.path.join(dic_path, href.split('/')[-1])
        download_link = href
        print("当前下载链接:", download_link)
        file_download(dic_path, download_link, file_path)

    import json
    list_path = '../../../Ingredient_Search/data_nmg/hrefs.json'
    with open(list_path, 'w', encoding='utf-8') as file:
        json.dump(hrefs, file, ensure_ascii=False, indent=4)  # 使用 ensure_ascii=False 保持中文字符

    driver.quit()

