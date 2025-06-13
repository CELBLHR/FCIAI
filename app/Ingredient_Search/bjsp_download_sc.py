import time

import os
from file_download import file_download
from selenium.webdriver.common.by import By

from tqdm import tqdm
from selenium_chrome import get_chrome_driver


def download_sc(url='https://scjgj.sc.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'scjgj/c104577/list.shtml'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)
    hrefs = []
    for i in range(4):
        time.sleep(1)
        elements = driver.find_elements(By.XPATH, "//a[contains(@title, '保健食品备案通告')]")
        hrefs.extend([element.get_attribute('href') for element in elements])
        print(len(hrefs))
        try:
            next_page_element = driver.find_element(By.XPATH,
                                                    "//a[contains(text(), '下一页') and contains(@class, 'pagination-index')]")

            next_page_element.click()
        except Exception as e:
            print(e, "未找到下一页链接")

    dic_path = '../../../Ingredient_Search/data_sc'
    download_hrefs = []
    for href in hrefs:
        driver.get(href)
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")


        download_hrefs.extend([link.get_attribute('href') for link in pdf_links])
        print(download_hrefs)

    for download_href in download_hrefs:
        download_url = download_href
        file_path = os.path.join(dic_path, download_href.split('/')[-1])
        print("正在下载>>>", file_path)
        file_download(dic_path, download_url, file_path)
    driver.quit()
