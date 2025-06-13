import time

import os
from file_download import file_download
import requests
from bs4 import BeautifulSoup
from selenium_chrome import get_chrome_driver
if __name__ == '__main__':

    url = "https://scjg.hubei.gov.cn/zfxxgk/zcwj/qtwj/202407/t20240718_5270985.shtml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Host': 'scjg.hubei.gov.cn',
        'Sec-Ch-Ua': '"Microsoft Edge";v="95", "Chromium";v="95", ";Not A Brand";v="99"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }

    driver = get_chrome_driver()
    driver.get(url)

    time.sleep(5)

    driver.quit()
    # Make the POST request



