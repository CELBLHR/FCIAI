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
def download_bj(url='https://scjgj.beijing.gov.cn/'):
    # 构造 URL
    if not url.endswith('/'):
        url += '/'
    url += 'cxfw/'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)

    time.sleep(1)
    # 提取页数
    wait = WebDriverWait(driver, 10)
    element = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//a[@title='保健食品相关查询']")))
    element.click()

    element = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//a[@href='javascript:;' and @data-value='T_BJSPQYBZBA' and @title='保健食品备案信息']")))

    # 找到元素并点击
    element.click()
    pages = []
    for i in range(10):
        try:
            elements = driver.find_elements(By.XPATH,
                                               "//a[contains(@title, '查询详情') or contains(text(), '查询详情')]")

            # 提取 href 属性
            for element in elements:
                pages.append(element.get_attribute('href'))
        except Exception as e:
            continue
        #print(pages)
        #print("当前页数:", i+1)
        try:
            # 找到下一页按钮并点击
            next_page_button = driver.find_element(By.XPATH, "//a[@title='下一页']")
            next_page_button.click()
            try:
                WebDriverWait(driver, 1).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                alert_text = alert.text
                print(f"Alert text: {alert_text}")
                alert.accept()  # 接受警告框
                break  # 如果警告框出现，退出循环
            except Exception as e:
                # 如果没有警告框出现，忽略此异常
                pass

        except Exception as e:
            print(f"An error occurred: {e}")

            break

    time.sleep(3)  # 等待最多10秒
    hrefs = []

    for page in pages:
        driver.get(page)
        elements = driver.find_elements(By.XPATH, '//a[contains(text(), ".pdf")]')

        # 提取 href 属性
        for element in elements:
            href = element.get_attribute('href')
            hrefs.append(href)

    dic_path = '../../../Ingredient_Search/data_bj'
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
