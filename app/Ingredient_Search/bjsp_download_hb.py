
import time
from selenium_chrome import get_chrome_driver
from selenium.webdriver.common.by import By
from file_download import file_download
def download_hb(url='http://scjg.hebei.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'node/933'

    chrome_web_driver = get_chrome_driver()
    driver = chrome_web_driver
    driver.get(url)
    time.sleep(2)
    # 第一页
    parent_element = driver.find_element(By.XPATH, '//*[@id="zfxxgk_body2"]/div[2]/div[3]/div[3]/div[2]/div/div/div')
    elements_with_href = parent_element.find_elements(By.TAG_NAME, 'a')
    hrefs = [element.get_attribute('href') for element in elements_with_href]
    titles = [element.get_attribute('title') for element in elements_with_href]
    url_list = []
    for href, title in zip(hrefs, titles):
        if "国产保健食品备案信息查询表" in title:
            time.sleep(3)
            url_list.append((href,title))
    next_page_href = None
    try:
        next_page_element = driver.find_element(By.XPATH,
                                                '//*[@id="zfxxgk_body2"]/div[2]/div[3]/div[3]/div[2]/div/div/div/div[21]/table/tbody/tr/td[6]/a')
        next_page_href = next_page_element.get_attribute('href')
        print("下一页链接:", next_page_href)
    except Exception as e:
        print("未找到下一页链接:", e)
    # 循环每一页处理
    while next_page_href is not None:
        print("当前链接:", next_page_href)
        driver.get(next_page_href)
        time.sleep(2)
        parent_element = driver.find_element(By.XPATH, '//*[@id="zfxxgk_body2"]/div[2]/div[3]/div[3]/div[2]/div/div/div')
        elements_with_href = parent_element.find_elements(By.TAG_NAME, 'a')
        hrefs = []
        titles = []
        for element in elements_with_href:
            href = element.get_attribute('href')
            hrefs.append(href)

            # 尝试查找 <div> 并提取 title，如果 <div> 不存在则跳过
            try:
                div_element = element.find_element(By.XPATH, './/div')
                title = div_element.get_attribute('title')
            except:
                title = ""  # 如果没有找到 <div>，将 title 设置为 None
            titles.append(title)
        for href, title in zip(hrefs, titles):
            if "国产保健食品备案信息查询表" in title:
                time.sleep(3)
                url_list.append((href, title))
        try:
            next_page_element = driver.find_element(By.XPATH,
                                                    '//*[@id="zfxxgk_body2"]/div[2]/div[3]/div[3]/div[2]/div/div/div/div[21]/table/tbody/tr/td[6]/a')
            next_page_href = next_page_element.get_attribute('href')
            print("下一页链接:", next_page_href)
            print(url_list)
        except Exception as e:
            print("未找到下一页链接:", e)
            next_page_href = None
    print(url_list)
    # 读取每个链接的内容，提取pdf链接
    pdf_url_list = []
    for i in url_list:
        page_url = i[0]
        driver.get(page_url)
        parent_element = driver.find_element(By.XPATH, '//*[@id="PrintArea"]/table/tbody')
        elements_with_href = parent_element.find_elements(By.TAG_NAME, 'a')
        hrefs = [element.get_attribute('href') for element in elements_with_href]
        pdf_url_list.extend(hrefs)

    print(pdf_url_list)
    for pdf_url in pdf_url_list:
        file_download('data_hb', pdf_url)
        print('正在下载', pdf_url)

    # 关闭驱动
    driver.quit()