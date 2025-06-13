import requests
from bs4 import BeautifulSoup
import json
import os

def download_gd(url='https://amr.gd.gov.cn/'):
    # 定义目标URL和POST数据
    if not url.endswith('/'):
        url += '/'
    url += 'gdzj-web/certificatesearch/cnhealthfoodfiling/queryListPage.do'
    post_data = {
        'page': '1',
        'limit': '10000',
        'productName': '',
        'filingPerson': '',
        'socialCreditCode': '',
        'filingNumber': '0',
        'startDate1': '',
        'endDate1': '',
        'filingPersonAddress': ''
    }

    # 发送POST请求
    response = requests.post(url, data=post_data)

    # 检查响应状态码
    if response.status_code == 200:
        # 解析HTML内容
        soup = BeautifulSoup(response.text, 'html.parser')

        # 这里可以添加代码来提取您需要的信息
        # 例如，打印整个HTML内容
        data_dict = json.loads(soup.get_text())

        attachment_ids = [item['attachment_id'] for item in data_dict['returnValue']['datas'] if
                          'attachment_id' in item]
        print(attachment_ids)
        attachment_ids = [x for x in attachment_ids if x is not None]
        print(len(attachment_ids))
    else:
        print(f'请求失败，状态码：{response.status_code}')
    dic_path = '../../../Ingredient_Search/data_gd'
    for id in attachment_ids:
        url = 'https://amr.gd.gov.cn/gdzj-web/component/upload.do?action=download'

        # 表单数据
        payload = {
            'filepath': '/data/upload/files/healthfoodfiling/' + id + '.pdf',
            'filename': id + '.pdf'
        }

        # 发送POST请求并下载文件
        try:
            response = requests.post(url, data=payload, stream=True)

            # 检查响应状态码
            if response.status_code == 200:
                # 打开文件用于写入
                with open(os.path.join(dic_path, payload['filename']), 'wb') as file:
                    # 以块的方式写入文件，防止内存溢出
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                print(f"文件 {payload['filename']} 下载成功。")
            else:
                print(f"请求失败，状态码：{response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"请求发生错误：{e}")

    size_limit = 10 * 1024  # 10 * 1024 bytes

    # 删除下载失败的文件
    for filename in os.listdir(dic_path):
        file_path = os.path.join(dic_path, filename)
        if os.path.isfile(file_path):
            try:
                file_size = os.path.getsize(file_path)
                if file_size < size_limit:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
