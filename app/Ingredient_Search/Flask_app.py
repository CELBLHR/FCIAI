from flask import Flask, render_template, request, jsonify, send_file
import json
import re
import os
from pathlib import Path
from flask_cors import CORS

# from bjsp_download_process import download_all
# from pdf_data_read import pdf_data_read_main
baseurl= os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Load the JSON data
def load_data(json_path):
    with open(json_path, 'r', encoding='UTF-8') as file:
        return json.load(file)


# Function to extract matching ingredient
def extract_ingredient(s, ingredient):
    ingredients = re.sub(r'(\(|\（)', ',', s)
    ingredients = re.sub(r'(\)|\）)', '', ingredients)
    ingredients = re.split(r'[、,，]', ingredients)
    ingredients = [ing.replace(' ', "") for ing in ingredients]
    #去掉类似于“又名”、“以”、“记”等词
    cleaned_ingredient_list = [re.sub(r'(又名|以|记)', '', ing) for ing in ingredients]

    for i in cleaned_ingredient_list:
        if ingredient in i:
            return i


# Function to clean the food name
def clean_food_name(food_name):

    return re.sub(r'备案入.*', '', food_name)



# Handle the search query
def search(request):
    query = request.strip()
    # 保健食品数据的JSON文件路径
    json_path = 'data_3/bjsp_dict_merged.json'
    json_path = os.path.normpath(os.path.join(baseurl, json_path))
    data = load_data(json_path)

    result_list = []
    for food_name, food_info in data.items():
        if query in food_info['ingredient']:
            match_content = extract_ingredient(food_info['ingredient'], query)
            if len(match_content) > 12:
                continue
            result_list.append({
                "food_name": clean_food_name(food_name),
                "path": food_info['path'].replace('\\', '/'),
                "match_content": match_content
            })
    result_list.sort(key=lambda x: len(x['match_content']))
    start_index = len(result_list) - len(result_list) // 3
    result_list[start_index:] = reversed(result_list[start_index:])

    if result_list:
        return jsonify(result_list)
    else:
        return jsonify({"error": "未找到对应的保健食品"})

# @app.route('/data_update', methods=['POST'])
# def data_update_process():
#     download_all()
#     pdf_data_read_main()

# Route to handle file download

def download_files(request):
    file_path = request.strip()
    file_path = os.path.normpath(os.path.join(baseurl, file_path))
    # Convert the file path to a valid OS path
    file_path = file_path.replace('\\', '/')
    # Check if the file exists
    if os.path.exists(file_path):
        # 获取文件名
        filename = os.path.basename(file_path)
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return jsonify({"error": "文件未找到"}), 404



# 拼接并规范化路径

