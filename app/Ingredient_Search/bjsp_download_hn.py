import os.path

import requests
import json
import warnings
from tqdm import tqdm
import time


def download_hn(url='https://222.143.32.212:8096/'):
    warnings.filterwarnings('ignore')
    if not url.endswith('/'):
        url += '/'
    url+= 'gongypPermit_loadYpXkz.action?comMc=&xkzbh=0'

    # 特别定义河南的下载函数
    def file_download(dic_path, bjsp_url, file_path=None):
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
    # url = "https://222.143.32.212:8096/gongypPermit_loadYpXkz.action?comMc=&xkzbh=0"
    headers = {

        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",

    }

    # Make the POST request
    response = requests.post(url, headers=headers, verify=False)

    # Check if the request was successful
    if response.status_code == 200:
        print("Request was successful.")
        # Print the content of the response
    else:
        print(f"Request failed with status code: {response.status_code}")

    data = json.loads(response.text)

    # 遍历rows列表，提取每个字典中的PATH值
    files = [item['PATH'] for item in data['rows']]

    download_base_url = r"https://222.143.32.212:8096/jsp/common/JSShow_pdf3.jsp?filePath="
    dic_path = r"../../../Ingredient_Search/data_hn"

    sleep_count = 0
    for f in tqdm(files, desc="下载进度"):
        tqdm.write("当前执行：{}".format(f))
        file_path = os.path.join(dic_path, f)
        download_url = download_base_url + f
        if os.path.exists(file_path):
            continue
        try:
            file_download(dic_path, download_url, file_path)
        except Exception as e:
            tqdm.write(f"处理文件{f}时出现错误：{e}")
            continue
        sleep_count += 1
        if sleep_count % 100 == 0:
            tqdm.write("暂停30s")
            time.sleep(30)