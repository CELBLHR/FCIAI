import time

import os
from file_download import file_download
from selenium.webdriver.common.by import By

from tqdm import tqdm
from selenium_chrome import get_chrome_driver


def download_hun(url='https://amr.hunan.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'amr/zwx/xxgkmlx/tzggx/index.html'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)

    page_list = []


    #调试用
    list_path = "../../../Ingredient_Search/data_hun/page_list.txt"
    if not os.path.exists(list_path):



        for i in range(50):
            time.sleep(1)
            elements = driver.find_elements(By.XPATH, "//a[contains(@title, '保健食品备案')]")
            # 遍历元素并打印每个元素的href属性
            for element in elements:
                href = element.get_attribute('href')
                page_list.append(href)
            print("当前链接:", page_list[-5:])

            try:
                next_page_element = driver.find_element(By.XPATH, "//a[contains(text(), '下一页')]")
                # 模拟点击该元素
                next_page_element.click()
                time.sleep(4)
            except Exception as e:
                print(e, "未找到下一页链接")
                break
            print("当前链接:", page_list[-5:])
        print(len(page_list))



        with open(list_path, 'w') as file:
            for item in page_list:
                file.write(str(item) + '\n')
    # 读取文件并恢复列表
    with open(list_path, 'r') as file:
        page_list = [str(line.strip()) for line in file]

    print(page_list)

    zip_list = []
    for page in page_list:
        time.sleep(1)
        print("当前链接:", page)
        driver.get(page)
        zip_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.zip')]")

        # 打印出找到的链接
        for link in zip_links:
            href = link.get_attribute('href')
            zip_list.append(href)
        # 下载zip文件
    print(zip_list)
    dic_path = '../../../Ingredient_Search/data_hun'
    for zip_file in zip_list:
        download_url = zip_file
        file_path = os.path.join(dic_path, zip_file.split('/')[-1])
        print("正在下载>>>", file_path)
        file_download(dic_path, download_url, file_path)

    # 获取dic_path目录下所有zip文件的绝对路径
    zip_files = [os.path.join(dic_path, f) for f in os.listdir(dic_path) if f.endswith('.zip')]
    # 解压zip文件

    # 解压zip文件
    import zipfile

    for file in zip_files:
        try:
            with zipfile.ZipFile(file, 'r') as zip_ref:
                zip_ref.extractall(dic_path)
        except Exception as e:
            print(f"解压{file}时出现错误：{e}")
            continue

    driver.quit()
