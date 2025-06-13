import time

import os
from file_download import file_download
from selenium.webdriver.common.by import By

from tqdm import tqdm
from selenium_chrome import get_chrome_driver

def download_jx(url="http://amr.jiangxi.gov.cn"):
    if not url.endswith('/'):
        url += '/'
    url += "col/col46347/index.html"

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    next_page_href = url

    page_list = []

    for i in range(8):
        driver.get(next_page_href)
        print("当前链接:", next_page_href)
        time.sleep(2)
        parent_element = driver.find_element(By.XPATH, '//*[@id="330273"]/div')
        elements_with_href = parent_element.find_elements(By.TAG_NAME, 'a')
        # 获取bjsp的pdf链接
        for element in elements_with_href:
            # 获取 'a' 标签的 title 属性
            title = element.get_attribute('title')
            # 获取 'a' 标签的 href 属性
            href = element.get_attribute('href')

            # 检查 title 是否包含“保健食品备案”
            if "保健食品备案" in title and href not in page_list:
                # 如果条件满足且列表中不存在href，将 href 添加到列表中
                page_list.append(href)

        next_page_element = driver.find_element(By.XPATH, '//*[@id="330273"]/table/tbody/tr/td/table/tbody/tr/td[8]')
        element = next_page_element.find_element(By.TAG_NAME, 'a')
        # 获取 'a' 标签的 title 属性
        title = element.get_attribute('title')
        # 获取 'a' 标签的 href 属性
        href = element.get_attribute('href')
        if "下页" in title:
            # 如果条件满足，将 href 添加到列表中
            next_page_href = href
        else:
            print("未找到下一页链接")
            break


        #  判断是否为最后一页
        from selenium.common.exceptions import NoSuchElementException

        try:
            last_page_tag = element.get_attribute('disabled')
            if last_page_tag:
                break
        except NoSuchElementException:
            # 如果捕获到异常，说明元素不存在或不可访问，继续执行循环
            continue
    zip_list = []
    for page in page_list:
        time.sleep(1)
        print("当前链接:", page)
        driver.get(page)
        try:
            elements = driver.find_elements(By.XPATH, "//a[contains(text(), '备案凭证')]")
            # 遍历找到的元素列表，并打印每个元素的href属性
            for element in elements:
                href = element.get_attribute('href')
                break
            zip_list.append(href)
        except Exception as e:
            print(f"处理网页{page}时出现错误：{e}")
            continue
    print(zip_list)

    dic_path = '../../../Ingredient_Search/data_jx'
    for zip_file in zip_list:
        download_url = zip_file

        file_path = os.path.join(dic_path, zip_file.split('=')[-1])
        print("正在下载>>>", file_path)
        file_download(dic_path, download_url, file_path)

    # 获取dic_path目录下所有zip文件的绝对路径
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
