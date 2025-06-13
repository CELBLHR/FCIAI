import time

from file_download import file_download
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from tqdm import tqdm
from selenium_chrome import get_chrome_driver
from selenium.webdriver.common.action_chains import ActionChains
import os
def download_ah(url='https://amr.ah.gov.cn/'):
    #  构造URL
    if not url.endswith('/'):
        url += '/'
    url += 'sjfb/qtsj/bjspbaxx/index.html'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    # 打开网页
    driver.get(url)
    page_list = []

    for i in range(5):
        time.sleep(1)
        elements = driver.find_elements(By.XPATH, "//a[contains(@title, '国产保健食品备案凭证')]")


        # 遍历找到的元素，并提取href属性
        for element in elements:
            href = element.get_attribute('href')
            page_list.append(href)
        # 模拟点击“下一页”链接
        try:
            next_page_link = driver.find_element(By.CSS_SELECTOR, 'a[aria-label="跳转至下一页"]')
        except Exception as e:
            print(e, "未找到下一页链接")
            break
        ActionChains(driver).click(next_page_link).perform()
        # 等待页面加载完成
        driver.implicitly_wait(5)
        print("当前链接:", page_list[-5:])

    zip_list = []
    for page in page_list:
        time.sleep(1)
        print("当前链接:", page)
        driver.get(page)
        element = driver.find_elements(By.XPATH, r'//*[@id="wenzhang"]/div[2]/p/a')

        href = element[0].get_attribute('href')
        zip_list.append(href)
    print(zip_list)

    # 下载zip文件
    dic_path = '../../../Ingredient_Search/data_ah'
    for url in zip_list:
        download_url = url
        file_path = os.path.join(dic_path, url.split('/')[-1])
        print("正在下载>>>", file_path)
        file_download(dic_path, download_url, file_path)

    # 获取dic_path目录下所有文件的绝对路径
    files = [os.path.join(dic_path, f) for f in os.listdir(dic_path)]
    # 选择出zip文件
    zip_files = [f for f in files if f.endswith('.zip')]
    # 解压zip文件
    import zipfile
    for file in zip_files:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall(dic_path)
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

