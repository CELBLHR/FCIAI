import os
import easyocr
import numpy as np
from PIL import Image
import re
import json
from tqdm import tqdm


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

def pdf_ocr_read_jl():
    fail_file_ckpt = '../../../Ingredient_Search/data_3/fail_files_ocr_jl.json'
    finished_province_ckpt = './data_3/finished_province_ocr_3.json'
    finished_file_ckpt = '../../../Ingredient_Search/data_3/finished_pdf_ocr_prov_3.json'
    bjsp_dict_ckpt = './data_3/bjsp_dict_origin.json'


    # 读取各种checkpoint文件

    # 读取已处理数据字典用于更新
    try:
        with open(bjsp_dict_ckpt, 'r', encoding='UTF-8') as file:
            loaded_set_as_json = file.read()
            bjsp_dict = json.loads(loaded_set_as_json)
    except FileNotFoundError:
        bjsp_dict = {}
        # 读取已处理省份

    # 初始化easyocr Reader，这里假设你的环境中已经安装了easyocr并且配置了GPU支持
    reader = easyocr.Reader(['en', 'ch_sim'], gpu=True)

    # 读取失败文件列表用于ocr处理
    fail_files = []

    # 图像文件所在的文件夹路径
    dic_path = r"../../../Ingredient_Search/data_jl"

    # 遍历文件夹中的所有文件
    for filename in tqdm(os.listdir(dic_path)):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):  # 检查文件扩展名
            file_path = os.path.join(dic_path, filename)
            print(f"正在处理文件 {file_path}")
            # 打开图像文件'
            try:

                image = Image.open(file_path)
            except Exception as e:
                print(f"处理文件 {filename} 时发生错误: 可能不是个图片文件")
                save_list_to_json([file_path], fail_file_ckpt)

                continue

            # 将PIL图像转换为numpy数组
            image_np = np.array(image)

            # 使用easyocr识别图像中的文字
            result = reader.readtext(image_np)

            # 初始化一个字符串来存储当前文件的文本
            full_text = ''

            for text in result:
                full_text += text[1] + '\n'

            # 这里你可以选择将full_text存储或打印出来
            full_text = full_text.replace("\n", "")

            pattern = r'(?:备|各|答)\d+\s*([^原料]+)'
            match = re.search(pattern, full_text)

            if match:
                # 提取匹配到的文本
                product_name = match.group(1)
                # 使用正则表达式删除括号以及其他非中文字符
                clean_product_name = re.sub(r'[^\u4e00-\u9fa5]', '', product_name).strip()
            else:
                fail_files.append(file_path)
                print(f"提取名称失败，文件名：{file_path}")
                save_list_to_json([file_path], fail_file_ckpt)
                continue

            try:
                pdf_file = file_path
                product_name = clean_product_name
                # print(product_name)
                if product_name in bjsp_dict:
                    continue
                # 提取成分
                data_text = full_text
                data_text = data_text.replace("\n", "")
                # 把【辅料】替换成逗号
                data_text = re.sub(r'辅料', ",", data_text)
                # 选择【原料】和下一个条目之间的内容
                pattern = re.compile(r'原料(.*?)(?:功效|标志|杯志|生产工艺)', re.S)
                match = pattern.search(data_text)
                if not match:
                    fail_file = pdf_file
                    print("提取成分失败，文件名：", pdf_file)
                    fail_files.append(fail_file)
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


            except Exception as e:
                print(f"处理文件 {pdf_file} 时发生错误: {e}")
                save_list_to_json([pdf_file], fail_file_ckpt)
                continue

            # # 保存已处理省份
            # save_list_to_json([province], finished_province_ckpt)
    print("处理完成")