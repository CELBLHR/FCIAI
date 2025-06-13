import requests
from bs4 import BeautifulSoup
import re
import os





def download_sd(url='http://amr.shandong.gov.cn/'):
    if not url.endswith('/'):
        url += '/'
    url += 'art/2020/1/17/art_93607_7214485.html'
    # 函数内特别定义下载函数
    def file_download(dic_path, bjsp_url, file_path=None):
        if file_path is not None and os.path.exists(file_path):
            print(f"文件{file_path}已存在，跳过下载")
            return
        if os.path.exists(dic_path) is False:
            os.mkdir(dic_path)
        download_bjsp_url = bjsp_url
        if file_path is None:
            file_name = os.path.join(dic_path, os.path.basename(bjsp_url))
        else:
            file_name = file_path
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
        }
        response = requests.get(download_bjsp_url, headers=headers, verify=False)
        # 确保请求成功
        if response.status_code == 200:
            # 将内容写入文件
            with open(file_name, 'wb') as file:
                file.write(response.content)
            # print(f'文件已成功下载并保存为 {json_filename}')
            # print(response.json())
        else:
            print(f'下载失败，服务器响应状态码：{response.status_code}')
    # Define the URL and the headers
    # url = "http://amr.shandong.gov.cn/art/2020/1/17/art_93607_7214485.html"
    headers = {

        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",

    }

    # Make the POST request
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful.")
        # Print the content of the response
    else:
        print(f"Request failed with status code: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    href_pattern = re.compile(r'/module/download/downfile\.jsp\?classid=\d+&filename=[\w\.]+\.zip')
    a_tags = soup.find_all('a', href=href_pattern)

    # 提取所有符合条件的href属性
    hrefs = [tag['href'] for tag in a_tags]

    # 打印所有找到的href
    # href = '/module/download/downfile.jsp?classid=0&filename=61393f95fa514ce2a0b2d7f017c727ec.zip'

    download_base_url = "http://amr.shandong.gov.cn"
    dic_path = '../../../Ingredient_Search/data_sd'
    for href in hrefs:
        download_url = download_base_url + href
        file_path = os.path.join(dic_path, href.split('=')[-1])
        print("正在下载>>>",file_path)
        file_download(dic_path, download_url, file_path)

    # 获取dic_path目录下所有文件的绝对路径
    files = [os.path.join(dic_path, f) for f in os.listdir(dic_path)]
    # 选择出zip文件
    zip_files = [f for f in files if f.endswith('.zip')]

    import zipfile
    for file in zip_files:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            zip_ref.extractall(dic_path)
        #os.remove(file)

