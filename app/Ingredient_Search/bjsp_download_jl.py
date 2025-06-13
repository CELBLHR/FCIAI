import time
import json
import os
from dataclasses import dataclass, asdict

from selenium import webdriver
from file_download import file_download


from selenium.webdriver.common.by import By

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def download_jl(url="http://scjg.jl.gov.cn"):

    if not url.endswith("/"):
        url += "/"
    url += "jianguan/bjsp/index.html"
    #内部特别定义driver
    def get_chrome_driver():
        chrome_driver_path = r"../../../Ingredient_Search/chromedriver-win64/chromedriver.exe"
        options = Options()
        options.add_argument("--incognito")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36")
        service = Service(chrome_driver_path)
        chrome_driver = webdriver.Chrome(service=service, options=options)

        return chrome_driver
    chrome_web_driver = get_chrome_driver()
    # 打开网页
    chrome_web_driver.get(url)


    driver = chrome_web_driver
    time.sleep(1)
    for i in range(2):


        parent_element = driver.find_element(By.XPATH, '/html/body/div[4]/div[2]/div/div/ul')
        elements_with_href = parent_element.find_elements(By.TAG_NAME, 'a')

        # 获取每个<a>标签的href属性
        hrefs = [element.get_attribute('href') for element in elements_with_href]
        titles = [element.get_attribute('title') for element in elements_with_href]

        # 打印所有找到的href属性
        for href,title in zip(hrefs,titles):
            if "吉林省保健食品备案公告" in title:
                print("当前执行：",title)
                time.sleep(3)


                driver.execute_script(f"window.open('{href}', '_blank');")
                handles = driver.window_handles
                new_tab_handle = handles[-1]
                driver.switch_to.window(new_tab_handle)
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="print"]/div/div'))
                    )
                    parent_element = driver.find_element(By.XPATH, '//*[@id="print"]/div/div')
                except Exception as e:
                    print(f"处理网页{title}时出现错误：{e}")
                    driver.close()
                    driver.switch_to.window(handles[0])
                    continue
                elements_with_href = parent_element.find_elements(By.TAG_NAME, 'a')
                bjsp_hrefs = [element.get_attribute('href') for element in elements_with_href]
                bjsp_titles = [element.get_attribute('title') for element in elements_with_href]
                jl_dic = r"./jl_data"
                for bjsp in bjsp_hrefs:
                    #print(bjsp)
                    try:
                        file_download(jl_dic, bjsp)
                    except Exception as e:
                        #print(f"处理文件{bjsp}时出现错误：{e}")
                        continue
                driver.close()
                driver.switch_to.window(handles[0])
        time.sleep(3)
        next_tab_info = driver.find_element(By.XPATH, '/html/body/div[4]/div[2]/div/div/ul/div[2]/div/div[6]')
        elements_with_href = next_tab_info.find_elements(By.TAG_NAME, 'a')
        next_tab_href = [element.get_attribute('href') for element in elements_with_href]
        if next_tab_href is None:
            break

        driver.execute_script(f"window.open('{next_tab_href[0]}', '_blank');")
        # 获取所有窗口句柄
        handles = driver.window_handles
        old_tab_handle = handles[0]
        new_tab_handle = handles[-1]
        # 切换到新窗口
        driver.switch_to.window(new_tab_handle)
        time.sleep(5)
        # 如果你想关闭旧窗口（例如，第一个窗口）
        driver.switch_to.window(old_tab_handle)
        driver.close()
        # 切换回新窗口，使它成为主窗口
        driver.switch_to.window(new_tab_handle)

    chrome_web_driver.chromedriver.quit()
