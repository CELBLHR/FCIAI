import os
import shutil

# 源文件夹路径
new_data_folder = './data_3'

# 目标文件夹路径
pdf_data_folder = './data'

pdf_extension = '.pdf'

# 遍历源文件夹中的所有文件
for filename in os.listdir(new_data_folder):

    if filename.endswith(pdf_extension):
        # 构建文件完整路径
        source_file_path = os.path.join(new_data_folder, filename)
        destination_file_path = os.path.join(pdf_data_folder, filename)

        # 使用shutil.move()移动文件
        shutil.move(source_file_path, destination_file_path)
        print(f'已移动文件：{filename}')
print('所有文件已移动完成。')
