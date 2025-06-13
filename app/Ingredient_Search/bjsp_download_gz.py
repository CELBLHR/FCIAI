import time

import os
from file_download import file_download
from selenium.webdriver.common.by import By

from tqdm import tqdm
from selenium_chrome import get_chrome_driver


def download_gz(url='https://amr.guizhou.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url+='zwgk/xxgkml/zdlyxx/spaq/index.html'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)
    hrefs = []
    for i in range(7):
        time.sleep(1)
        try:
            # 只有一个条目
            elements = driver.find_elements(By.XPATH, "//a[contains(@title, '保健食品备案')]")
            hrefs.extend([element.get_attribute('href') for element in elements])
            href = hrefs[-1]
            break

        except Exception as e:
            next_page_element = driver.find_element(By.XPATH,
                                                    "//a[contains(text(), '下一页')")
            next_page_element.click()
            print(e, "未找到下一页链接")


    try:
        download_hrefs = []
        driver.get(href)
        pdf_links = driver.find_elements(By.XPATH, "//a[contains(@title, '保健食品备案')]")
        download_hrefs.extend([link.get_attribute('href') for link in pdf_links])
        print(download_hrefs)
    except Exception as e:
        print(e, "未找到链接")


    dic_path = '../../../Ingredient_Search/data_gz'
    for download_href in download_hrefs:
        download_url = download_href
        file_path = os.path.join(dic_path, download_href.split('/')[-1])
        print("正在下载>>>", file_path)
        file_download(dic_path, download_url, file_path)

    zip_files = [os.path.join(dic_path, f) for f in os.listdir(dic_path) if f.endswith('.zip')]

    # 解压zip文件
    import zipfile

    for file in zip_files:
        try:
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(dic_path)
        except Exception as e:
            print(f"解压{file}时出现错误：{e}")
            continue
    # 把PDF文件移动到根文件夹下
    import shutil

    for root, dirs, files in os.walk(dic_path):
        for file in files:
            # 检查文件是否为PDF
            if file.lower().endswith('.pdf'):
                # 原始PDF文件的完整路径
                original_file_path = os.path.join(root, file)
                # 目标路径（移动到原始文件夹）
                destination_path = os.path.join(dic_path, file)
                # 移动文件
                shutil.move(original_file_path, destination_path)

    driver.quit()
