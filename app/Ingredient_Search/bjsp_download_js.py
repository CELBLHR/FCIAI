

import configparser
import re
from bs4 import BeautifulSoup
import requests
import json
import os

# 附件的本地保存路径
# local_filename = './downloaded_bjsp.json'


def json_download(json_filename, bjsp_url):
    download_bjsp_url = bjsp_url +"HealthFoodServlet.json?healthFoodQuery=true&date " +("=1722232969097&page=1&limit"
                                                                                      "=2000&BJ_FOOD_NAME=&RECORD_NO=&RECORD_MAN_NAME=")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0'
    }
    response = requests.get(download_bjsp_url, headers=headers)
    # 确保请求成功
    if response.status_code == 200:
        # 将内容写入文件
        with open(json_filename, 'wb') as file:
            file.write(response.content)
        # print(f'文件已成功下载并保存为 {json_filename}')
        # print(response.json())
    else:
        print(f'下载失败，服务器响应状态码：{response.status_code}')





def read_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data





def pdf_download(json_path: str, bjsp_url: str, dic_path: str):
    # 使用示例
    # 请求的URL
    # bjsp_url = 'http://www.jsgsj.gov.cn:1100/healthfood-web/HealthFoodServlet.json?healthFoodDetailQuery=true&date' \
               #'=1722243264232&zhuJian='
    download_bjsp_url = bjsp_url + 'HealthFoodServlet.json?healthFoodDetailQuery=true&date' +\
               '=1722243264232&zhuJian='

    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': 'JSESSIONID=-xj9pSlVUVy9MK3_MJB1xK7eMZOPXFKBtKdu9Ch4HZ5bAkQnXI4r!1048707457!1722242378069',
        'Host': 'www.jsgsj.gov.cn:1100',
        'Origin': 'http://www.jsgsj.gov.cn:1100',
        'Proxy-Connection': 'keep-alive',
        'Referer': 'http://www.jsgsj.gov.cn:1100/healthfood-web/page/bjsp/bjspDetail.jsp?',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
        'X-Requested-With': 'XMLHttpRequest'
    }
    try:

        json_data = read_json_file(json_path)
        # 提取BJ_FOOD_NAME和ID对
        food_id_pairs = [(item['BJ_FOOD_NAME'], item['ID'], item['RN']) for item in json_data['data']]
        for food_name, food_id, index in food_id_pairs:
            if '童年故事' in food_name:
                continue
            # 处理食品名称，去除特殊字符
            food_name = food_name.replace('<sup>®</sup>', '')
            food_name = food_name.replace('<sub>', '')
            food_name = food_name.replace('</sub>', '')
            food_name = food_name.replace(' ', '')
            print(f'正在下载第{index}个文件：{food_name}')
            target_url = download_bjsp_url + food_id
            # 发送POST请求
            response = requests.get(target_url, headers=headers)

            # 检查响应状态码
            if response.status_code == 200:
                data = response.content
                soup = BeautifulSoup(data, 'html.parser')

                durl_pattern = re.compile(r'"FILE_LOCATION":"(.*?)","REMARK"', re.S)
                durl = re.findall(durl_pattern, soup.prettify())[0]

            else:
                print(f'Failed to retrieve data: {response.status_code}')
            download_url = bjsp_url +'download.jsp?help=bjsp&location=' + durl.replace(
                '\\', '')

            response = requests.get(download_url, headers=headers)
            if response.status_code == 200:
                # 如果文件不存在则下载
                if not os.path.exists(dic_path + f'/{index}_{food_name}.pdf'):
                    with open(dic_path + f'/{index}_{food_name}.pdf', 'wb') as file:
                        file.write(response.content)
    finally:
        return



def download_js():
    json_path = './data_2/json_table_js.json'
    pdf_dic = './data_js'

    # 读取配置文件, 获取url
    ini_path = '../../../Ingredient_Search/data_2/my_config.ini'
    config = configparser.ConfigParser()
    config.read(ini_path, encoding='utf-8')

    #得到js对应url头部
    bjsp_url = config['url_config']['main_url']
    if not bjsp_url.endswith('/'):
        bjsp_url += '/'

    # 下载bjsp表
    json_download(json_filename=json_path, bjsp_url=bjsp_url)
    # 使用bjsp表下载pdf
    pdf_download(json_path=json_path, bjsp_url=bjsp_url, dic_path=pdf_dic)
