import time

import os
from file_download import file_download
from selenium.webdriver.common.by import By

from tqdm import tqdm
from selenium_chrome import get_chrome_driver





def download_yn(url='https://amr.yn.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'zwgk/fdzdgknr/xzxk.htm'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)
    hrefs = []

    time.sleep(1)
    elements = driver.find_elements(By.XPATH, "//a[contains(@title, '国产保健食品备案公告')]")
    hrefs.extend([element.get_attribute('href') for element in elements])
    print(len(hrefs))

    # 提取所有href属性和文件名
    attachments = []
    for page in hrefs:
        print(page)
        driver.get(page)
        time.sleep(1)
        try:
            attachment_links = driver.find_elements(By.XPATH,
                                                    "//div[contains(@class, 'fj') and contains(., '保健食品备案凭证')]/span/a")


            for element in attachment_links:
                href = element.get_attribute('href')
                file_name = element.find_element(By.XPATH, ".//span").text
                if '.zip' in file_name:
                    attachments.append({'href': href, 'file_name': file_name})
        except Exception as e:
            print(e, "未找到附件链接")
            continue

    dic_path = '../../../Ingredient_Search/data_yn'
    for download_bi in attachments:
        download_url = download_bi['href']
        file_path = os.path.join(dic_path, download_bi['file_name'])
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