import os.path

from bs4 import BeautifulSoup
import requests
from file_download import file_download

def download_ln(url='http://tsgs.lnspaq.com/'):
    if not url.endswith('/'):
        url += '/'
    url += 'BeiAn2022_Sheng_list.aspx'
    # 第一次 GET 请求获取初始页面
    #url = "http://tsgs.lnspaq.com/BeiAn2022_Sheng_list.aspx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # 提取隐藏字段 __VIEWSTATE 和 __EVENTVALIDATION 的值
    viewstate = soup.find(id="__VIEWSTATE")["value"]
    eventvalidation = soup.find(id="__EVENTVALIDATION")["value"]

    pdf_list = []
    for i in range(1, 12):
        data = {
            "__VIEWSTATE": viewstate,
            "__EVENTVALIDATION": eventvalidation,
            "__EVENTTARGET": "AspNetPager1",  # 分页控件
            "__EVENTARGUMENT": str(i),           # 页码，3表示第三页

        }

        response = requests.post(url, headers=headers, data=data)
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all('a', href=True)
        if links is None:
            continue
        # 遍历所有找到的<a>标签
        for link in links:
            # 获取href属性值
            href = link['href']
            # 检查是否是我们需要的链接
            if href.endswith('.pdf'):
                pdf_list.append(href)
                print("加入", href)
    dic_path = '../../../Ingredient_Search/data_ll'
    if os.path.exists(dic_path) is False:
        os.mkdir(dic_path)
    for pdf_url in pdf_list:
        file_download(dic_path, pdf_url)
        print('正在下载', pdf_url)


