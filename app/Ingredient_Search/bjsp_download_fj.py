import time

import os
from file_download import file_download
from selenium.webdriver.common.by import By

from tqdm import tqdm
from selenium_chrome import get_chrome_driver

def download_fj(url='https://scjgj.fujian.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'zw/tzgg/'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)
    page_list = []
    for i in range(2):
        time.sleep(1)
        # 在页面上模拟搜索
        search_box = driver.find_element(By.CSS_SELECTOR, '.form_control.b-free-read-leaf')
        search_box.send_keys('国产保健')
        search_button = driver.find_element(By.CSS_SELECTOR, '.btn_base.btn_primary.b-free-read-leaf')
        search_button.click()
        time.sleep(5)
        # 提取所有包含“食品产品备案公告”的链接

        # 查找所有匹配的元素
        elements = driver.find_elements(By.XPATH, "//a[contains(@title, '食品产品备案公告')]")
        # 遍历元素并打印每个元素的href属性
        for element in elements:
            href = element.get_attribute('href')
            page_list.append(href)
        print("当前链接:", page_list[-5:])
        # 寻找下一页
        try:
            next_page_element = driver.find_element(By.XPATH, "//li[@class='next']/a")
            # 模拟点击该元素
            next_page_element.click()
        except Exception as e:
            print(e, "未找到下一页链接")
            break
    zip_list = []
    for page in page_list:
        time.sleep(1)
        print("当前链接:", page)
        driver.get(page)
        elements = driver.find_elements(By.XPATH, "//a[contains(text(), '备案凭证')]")

        for element in elements:
            href = element.get_attribute('href')
            zip_list.append(href)
    # 下载zip文件
    dic_path = '../../../Ingredient_Search/data_fj'
    for url in zip_list:
        download_url = url
        file_path = os.path.join(dic_path, url.split('/')[-1])
        print("正在下载>>>", file_path)
        file_download(dic_path, download_url, file_path)
    # 解压zip文件
    zip_files = [os.path.join(dic_path, f) for f in os.listdir(dic_path) if f.endswith('.rar')]
    import subprocess

    unrar_path = r'../../../Ingredient_Search/unrar/UnRAR.exe'
    for file in zip_files:
        try:
            subprocess.run([unrar_path, 'e', '-o+', file, dic_path])
        except Exception as e:
            print(f"解压{file}时出现错误：{e}")
            continue


    driver.quit()
