import os
import pdfplumber
import re
import json
from tqdm import tqdm

import easyocr
from pdf2image import convert_from_path
import numpy as np
import re
import json
from tqdm import tqdm

from pdf_ocr_read_jl import pdf_ocr_read_jl
from pdf_ocr_read_hun import pdf_ocr_read_hun
pdf_data_origin = [
    'ah',

    'fj',
    'gd',
    'hn',
    'js',
    'jx',
    'll',
    'sd',
    'sh',
    'tj',
    'yn',

]
pdf_data_img = [
    'gx',
    'bj',
    'gz',  # 不清晰
    'hb',
    'hlj',
    'nmg',
    'sc',
    'sx',
    'xj',
    'cq',

]
pdf_other = [
    'hun',
    'shanxi2',
    'jl'
]
bjsp_dict = {}
fail_files = []

fail_files_ckpt = './data_3/fail_files_origin.json'
finished_province_ckpt = './data_3/finished_province.json'
bjsp_dict_ckpt = './data_3/bjsp_dict_origin.json'
def save_dict_to_json(dictionary, filename):
    try:
        # 尝试读取现有文件内容
        try:
            with open(filename, 'r', encoding='UTF-8') as json_file:
                # 如果文件存在，读取内容
                existing_data = json.load(json_file)
        except FileNotFoundError:
            # 如果文件不存在，初始化为空字典
            existing_data = {}
        existing_data.update(dictionary)
        # 将合并后的数据写回文件
        with open(filename, 'w', encoding='UTF-8') as json_file:
            json.dump(existing_data, json_file, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存到文件 {filename} 时发生错误: {e}")


def save_list_to_json(new_list: list, filename):
    try:
        # 尝试读取现有文件内容
        try:
            with open(filename, 'r', encoding='UTF-8') as json_file:
                # 如果文件存在，读取内容
                existing_data = json.load(json_file)
        except FileNotFoundError:
            # 如果文件不存在，初始化为空列表
            existing_data = []

        # 检查现有数据是否为列表
        if not isinstance(existing_data, list):
            raise ValueError("文件内容不是列表，无法合并")
        # 合并新列表
        existing_data.extend(new_list)
        existing_data = list(set(existing_data))
        # 将合并后的列表写回文件
        with open(filename, 'w', encoding='UTF-8') as json_file:
            json.dump(existing_data, json_file, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存到文件 {filename} 时发生错误: {e}")
def read_checkpoints() -> list:
    try:
        with open(finished_province_ckpt, 'r', encoding='UTF-8') as file:
            ckpt_as_json = file.read()
            loaded_ckpt = json.loads(ckpt_as_json)
    except FileNotFoundError:
        loaded_ckpt = []

    return loaded_ckpt


def pdfs_read_origin():
    finished_province = read_checkpoints()
    for province in tqdm(pdf_data_origin, desc=f'Processing provinces'):
        # 跳过已处理省份
        # if province in finished_province:
        #     print(f'{province} has been processed, skipping...')
        #     continue
        tqdm.write(f'Processing {province}...')
        pdf_dic_path = f'./data_{province}'
        pdf_file_list = [os.path.join(pdf_dic_path, pdf_file) for pdf_file in os.listdir(pdf_dic_path) if
                         pdf_file.endswith('.pdf')]
        for pdf_file in pdf_file_list:
            try:
                with pdfplumber.open(pdf_file) as pdf:
                    # 提取产品名称
                    name_text = pdf.pages[0].extract_text().replace("\n", "")
                    name_pattern = r"产品名称\s*(.*?)\s*备案人"

                    # 使用re.search找到匹配的内容
                    match = re.search(name_pattern, name_text)

                    # 如果找到匹配的内容，提取并消除空格
                    if not match:
                        fail_file = pdf_file
                        fail_files.append(fail_file)
                        print("提取名称失败，文件名：", fail_file)
                        save_list_to_json([fail_file], fail_files_ckpt)
                        continue

                    product_name = match.group(1).replace(" ", "")
                    # print(product_name)

                    # 提取成分
                    data_text = pdf.pages[1].extract_text()
                    if '保健食品产品说明书' not in data_text:
                        # 如果第一页不是产品说明书，尝试提取第二页
                        data_page = pdf.pages[2]
                        data_text = data_page.extract_text()
                        if '保健食品产品说明书' not in data_text:
                            # 如果第二页也不是产品说明书，可能是图片形式的PDF
                            fail_file = pdf_file
                            fail_files.append(fail_file)
                            print("提取成分失败，文件名：", pdf_file)
                            save_list_to_json([fail_file], fail_files_ckpt)
                            continue
                    data_text = data_text.replace("\n", "")
                    # 把【辅料】替换成逗号
                    data_text = re.sub(r'【辅料】', ",", data_text)
                    # 选择【原料】和下一个条目之间的内容
                    pattern = re.compile(r'(?:【原料】)(.*?)(?:【)', re.S)
                    match = pattern.search(data_text)
                    if not match:
                        fail_file = pdf_file
                        print("提取成分失败，文件名：", pdf_file)
                        save_list_to_json([fail_file], fail_files_ckpt)
                        continue
                    ingredients = match.group(1)
                    # print(ingredients)

                    if product_name not in bjsp_dict:
                        # 更新字典
                        bjsp_dict[product_name] = {
                            'path': pdf_file,
                            'ingredient': ingredients
                        }
                        save_dict_to_json(bjsp_dict, bjsp_dict_ckpt)
            except Exception as e:
                print(f"处理文件 {pdf_file} 时发生错误: {e}")
                fail_files.append(pdf_file)
                continue



        #保存已处理省份
        save_list_to_json([province], './data_3/finished_province.json')

        with open('../../../Ingredient_Search/data_3/bjsp_dict_test.json', 'r', encoding='UTF-8') as file:
            loaded_set_as_json = file.read()
            loaded_set = json.loads(loaded_set_as_json)

def pdfs_read_ocr():
    reader = easyocr.Reader(['en', 'ch_sim'], gpu=True)
    # 读取失败文件列表用于ocr处理
    # with open('./data_3/fail_files_ocr_prov.json', 'r', encoding='UTF-8') as file:
    #     loaded_set_as_json = file.read()
    #     file_list = json.loads(loaded_set_as_json)
    # 读取已处理文件列表
    fail_file_ckpt = './data_3/fail_files_ocr.json'
    finished_province_ckpt = './data_3/finished_province.json'
    finished_file_ckpt = './data_3/finished_pdf_ocr.json'
    bjsp_dict_ckpt = './data_3/bjsp_dict_origin.json'
    file_list_path = './data_3/fail_files_origin.json'

    # 读取各种checkpoint文件
    # 读取已处理文件列表
    try:
        with open(finished_file_ckpt, 'r', encoding='UTF-8') as file:
            loaded_set_as_json = file.read()
            finished_pdf = json.loads(loaded_set_as_json)
    except FileNotFoundError:
        finished_pdf = []
    # 读取已处理数据字典用于更新
    try:
        with open(bjsp_dict_ckpt, 'r', encoding='UTF-8') as file:
            loaded_set_as_json = file.read()
            bjsp_dict = json.loads(loaded_set_as_json)
    except FileNotFoundError:
        bjsp_dict = {}
        # 读取已处理省份
    try:
        with open(finished_province_ckpt, 'r', encoding='UTF-8') as file:
            loaded_set_as_json = file.read()
            finished_province = json.loads(loaded_set_as_json)
    except FileNotFoundError:
        finished_province = []
    fail_files = []

    try:
        with open(file_list_path, 'r', encoding='UTF-8') as file:
            loaded_set_as_json = file.read()
            file_list = json.loads(loaded_set_as_json)
    except FileNotFoundError:
        file_list = []

    for province in pdf_data_img:
        #跳过已处理省份
        # if province in finished_province:
        #     print(f"省份 {province} 已处理，跳过")
        #     continue
        pdf_files = []
        province_path = f"./data_{province}"
        file_list.extend([os.path.join(province_path, file) for file in os.listdir(province_path) if file.endswith('.pdf')])


    # 处理对应省份的数据
    for file in tqdm(file_list):
        pdf_path = file
        if pdf_path in finished_pdf:
            # print(f"文件 {pdf_path} 已处理，跳过")
            continue
        # 将PDF文件转换为图像列表
        try:
            images = convert_from_path(pdf_path, first_page=1, last_page=3,
                                       poppler_path=r'../../../Ingredient_Search/poppler/poppler-24.08.0/Library/bin')
        except Exception as e:
            #print(f"处理文件 {pdf_path} 时发生错误: 可能不是个PDF文件")
            continue

        # 初始化一个字符串来存储所有文本
        full_text = ''
        # 保存已经处理的pdf
        save_list_to_json([pdf_path], finished_file_ckpt)
        # 遍历图像并使用easyocr进行文字识别
        for image in images:
            # 将PIL图像转换为numpy数组
            image_np = np.array(image)

            # 使用easyocr识别图像中的文字
            result = reader.readtext(image_np)
            for text in result:
                full_text += text[1] + '\n'

        # 提取产品名称和成分
        try:
            pdf_file = pdf_path
            text = full_text.replace("\n", "")
            # print(text)
            name_pattern = r"名称\s*(.*?)\s*(备|各)"
            # 使用re.search找到匹配的内容
            match = re.search(name_pattern, text)
            # 如果找到匹配的内容，提取并消除空格
            if not match:
                fail_file = pdf_file
                save_list_to_json([fail_file], fail_file_ckpt)
                #print("提取名称失败，文件名：", fail_file)
                continue

            product_name = match.group(1).replace(" ", "")
            # print(product_name)
            if product_name in bjsp_dict:
                continue
            # 提取成分
            data_text = text
            if '保健食品产品说明书' not in data_text:
                # 如果第一页不是产品说明书，尝试提取第二页
                fail_file = pdf_file
                save_list_to_json([fail_file], fail_file_ckpt)
                #print("提取成分失败，文件名：", pdf_file)
                # continue
            data_text = data_text.replace("\n", "")
            # 把【辅料】替换成逗号
            data_text = re.sub(r'辅料', ",", data_text)
            # 选择【原料】和下一个条目之间的内容
            pattern = re.compile(r'原料(.*?)(?:功效|标志|杯志|生产工艺)', re.S)
            match = pattern.search(data_text)
            if not match:
                fail_file = pdf_file
                #print("提取成分失败，文件名：", pdf_file)
                save_list_to_json([fail_file], fail_file_ckpt)
                continue

            ingredients = match.group(1)

            cleaned_ingredients = re.sub(r'[^\u4e00-\u9fa5,，]', '', ingredients)
            # print(ingredients)
            temp_dict = {}
            if product_name not in bjsp_dict:
                # 更新字典
                bjsp_dict[product_name] = {
                    'path': pdf_file,
                    'ingredient': cleaned_ingredients
                }
                # 保存提取的成分字典
                save_dict_to_json(bjsp_dict, bjsp_dict_ckpt)
                # 保存失败文件列表

        except Exception as e:
            #print(f"处理文件 {pdf_file} 时发生错误: {e}")
            save_list_to_json([pdf_file], fail_file_ckpt)
            continue

        # # 保存已处理省份
        # save_list_to_json([province], finished_province_ckpt)
    print("处理完成")

def pdf_data_read_main():
    pdfs_read_origin()
    pdfs_read_ocr()
    pdf_ocr_read_jl()
    pdf_ocr_read_hun()
