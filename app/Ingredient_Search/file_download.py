import os.path

import requests

# json的URL

# 附件的本地保存路径
# local_filename = './downloaded_bjsp.json'


def file_download(dic_path, bjsp_url, file_path=None):
    # 创建文件夹
    if os.path.exists(dic_path) is False:
        os.mkdir(dic_path)
    download_bjsp_url = bjsp_url
    if file_path is None:
        file_name = os.path.join(dic_path, os.path.basename(bjsp_url))
    else:
        file_name = file_path
    # 如果文件已存在，则跳过下载
    if os.path.exists(file_name):
        print(f"文件{file_name}已存在，跳过下载")
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
    }
    response = requests.get(download_bjsp_url, headers=headers)
    # 确保请求成功
    if response.status_code == 200:
        # 将内容写入文件
        with open(file_name, 'wb') as file:
            file.write(response.content)
        # print(f'文件已成功下载并保存为 {json_filename}')
        # print(response.json())
    else:
        print(f'下载失败，服务器响应状态码：{response.status_code}')

