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
def download_nmg(url='https://amr.nmg.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'nmg_dept_search/#/Door?keywords=%E4%BF%9D%E5%81%A5%E9%A3%9F%E5%93%81%E5%A4%87%E6%A1%88%E7%9A%84%E9%80%9A%E5%91%8A&siteTag=1&siteid=95'

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
                                        '//a[contains(., "保健食品") and contains(., "备案") and contains(., "通告")]')

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
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")

        # 提取并打印href属性
        for link in pdf_links:
            href = link.get_attribute('href')
            hrefs.append(href)

    print(hrefs)

    dic_path = '../../../Ingredient_Search/data_nmg'
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

