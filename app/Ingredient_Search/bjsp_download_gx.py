import time

import os
from file_download import file_download
from selenium.webdriver.common.by import By

from tqdm import tqdm
from selenium_chrome import get_chrome_driver


def download_gx(url='http://scjdglj.gxzf.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url+='sjcx/spjggxxcx/'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)
    hrefs = []
    pages = []

    time.sleep(1)
    elements = driver.find_elements(By.XPATH, "//a[contains(@title, '保健食品备案')]")
    pages.extend([element.get_attribute('href') for element in elements])
    for page in pages:
        driver.get(page)
        time.sleep(1)
        elements = driver.find_elements(By.XPATH, '//a[contains(@href, ".pdf")]')

        # 提取 href 属性
        for element in elements:
            href = element.get_attribute('href')
            hrefs.append(href)
    print(len(hrefs))

    dic_path = '../../../Ingredient_Search/data_gx'

    for download_href in hrefs:
        download_url = download_href
        file_path = os.path.join(dic_path, download_href.split('/')[-1])
        print("正在下载>>>", file_path)
        file_download(dic_path, download_url, file_path)
    driver.quit()
