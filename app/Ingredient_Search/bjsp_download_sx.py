import time
import json
import os
from dataclasses import dataclass, asdict

from selenium import webdriver
from file_download import file_download

from selenium.webdriver.common.by import By

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from tqdm import tqdm
from selenium_chrome import get_chrome_driver
def download_sx(url='https://scjgj.shanxi.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'wsfw/bszn/bjspba/index.shtml'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    next_page_href = url
    pdf_hrefs = []
    time.sleep(1)


    for i in range(6):
        driver.get(next_page_href)
        # 查找下一页地址
        try:
            next_page_link = driver.find_element(By.XPATH, "//a[contains(text(), '下一页')]")
            next_page_href = next_page_link.get_attribute('href')
        except Exception as e:
            print(e, "未找到下一页链接")
            break

        print("当前链接:", next_page_href)
        time.sleep(1)
        parent_element = driver.find_element(By.XPATH, '//*[@id="queryList"]/ul/table/tbody')
        elements_with_href = parent_element.find_elements(By.TAG_NAME, 'a')

        # 获取bjsp的pdf链接
        pdf_hrefs.extend([element.get_attribute('href') for element in elements_with_href if
                     element.get_attribute('href').endswith('.pdf')])
        print("当前链接:", pdf_hrefs[-5:])
    dic_path = '../../../Ingredient_Search/data_sx'
    for href in tqdm(pdf_hrefs):
        download_url = href
        file_path = os.path.join(dic_path, href.split('/')[-1])
        print("正在下载>>>", file_path)
        file_download(dic_path, download_url)


    driver.quit()
