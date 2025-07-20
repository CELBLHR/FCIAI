# 文件名: uno_formatter.py
import uno
import os
import sys
import json
import argparse
from com.sun.star.connection import NoConnectException
from com.sun.star.awt import FontWeight
from com.sun.star.beans import PropertyValue

# --- 连接和核心逻辑 ---

def connect_to_libreoffice():
    # (与之前相同的连接代码)
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context)
    try:
        return resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    except NoConnectException:
        print("UNO Error: 连接 LibreOffice 失败。", file=sys.stderr)
        sys.exit(1)


def extract_formatting(ppt_path: str, output_json_path: str, page_indices: list):
    """提取模式：读取格式并存为JSON"""
    context = connect_to_libreoffice()
    desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)
    presentation = None
    all_shapes_data = []

    try:
        props = (PropertyValue(Name='ReadOnly', Value=True),) # 这是正确行
        presentation = desktop.loadComponentFromURL(uno.systemPathToFileUrl(ppt_path), "_blank", 0, props)
        slides = presentation.getDrawPages()

        for page_idx in page_indices:
            if not (0 <= page_idx < slides.getCount()):
                continue
            slide = slides.getByIndex(page_idx)

            # 使用 enumerate 获取 shape 的索引作为唯一标识
            for shape_idx, shape in enumerate(slide):
                if not shape.supportsService("com.sun.star.drawing.TextShape"):
                    continue

                shape_data = {
                    "page_index": page_idx,
                    "shape_index": shape_idx,
                    "paragraphs": []
                }

                # 遍历段落
                p_enum = shape.Text.createEnumeration()
                while p_enum.hasMoreElements():
                    p = p_enum.nextElement()  # 这是一个段落对象
                    run_enum = p.createEnumeration()
                    runs_data = []
                    while run_enum.hasMoreElements():
                        run = run_enum.nextElement()  # 这是一个Run对象
                        if not run.getString(): continue

                        escapement = run.CharEscapement
                        script_type = 'superscript' if escapement > 0 else 'subscript' if escapement < 0 else 'normal'

                        runs_data.append({
                            "text": run.getString(),
                            "font_name": run.CharFontName,
                            "font_size": round(run.CharHeight, 1),
                            "is_bold": run.CharWeight > 149.0,
                            "is_italic": run.CharPosture.value != 'NORMAL',
                            "color_hex": f'#{run.CharColor:06X}',
                            "script_type": script_type,
                        })

                if runs_data:
                    shape_data["paragraphs"].append({"runs": runs_data})

                if shape_data["paragraphs"]:
                    all_shapes_data.append(shape_data)

        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(all_shapes_data, f, ensure_ascii=False, indent=2)
        print(f"UNO: 格式提取完成，已保存到 {output_json_path}")

    finally:
        if presentation:
            presentation.close(True)


def apply_translations(input_ppt_path: str, translated_json_path: str, output_ppt_path: str):
    """应用模式：读取JSON，将译文和格式写回PPT"""
    context = connect_to_libreoffice()
    desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)
    presentation = None

    with open(translated_json_path, 'r', encoding='utf-8') as f:
        all_shapes_data = json.load(f)

    try:
        presentation = desktop.loadComponentFromURL(uno.systemPathToFileUrl(input_ppt_path), "_blank", 0, ())
        slides = presentation.getDrawPages()

        for shape_data in all_shapes_data:
            page_idx = shape_data['page_index']
            shape_idx = shape_data['shape_index']

            slide = slides.getByIndex(page_idx)
            shape = slide.getByIndex(shape_idx)
            text = shape.Text

            # 清空整个文本框的所有内容
            cursor = text.createTextCursor()
            cursor.gotoStart(False)
            cursor.gotoEnd(True)  # 选中所有文本
            text.insertString(cursor, "", False)  # 用空字符串替换

            # 逐段、逐Run地重新构建内容
            for p_data in shape_data['paragraphs']:
                for run_info in p_data['runs']:
                    cursor.gotoEnd(False)  # 移动到末尾
                    # 设置格式
                    cursor.CharFontName = run_info['font_name']
                    cursor.CharHeight = run_info['font_size']
                    cursor.CharWeight = FontWeight.BOLD if run_info['is_bold'] else FontWeight.NORMAL
                    cursor.CharPosture = uno.enum('com.sun.star.awt.FontSlant', 'ITALIC') if run_info[
                        'is_italic'] else uno.enum('com.sun.star.awt.FontSlant', 'NONE')
                    cursor.CharColor = int(run_info['color_hex'].lstrip('#'), 16)

                    if run_info['script_type'] == 'superscript':
                        cursor.CharEscapement = 33
                        cursor.CharEscapementHeight = 58
                    elif run_info['script_type'] == 'subscript':
                        cursor.CharEscapement = -33
                        cursor.CharEscapementHeight = 58
                    else:
                        cursor.CharEscapement = 0
                        cursor.CharEscapementHeight = 100

                    # 写入译文
                    text.insertString(cursor, run_info['translated_text'], False)

                # 在段落末尾插入段落符（如果不是最后一个段落）
                cursor.gotoEnd(False)
                text.insertControlCharacter(cursor, uno.enum('com.sun.star.text.ControlCharacter', 'PARAGRAPH_BREAK'),
                                            False)

        # 另存为最终文件
        presentation.storeAsURL(uno.systemPathToFileUrl(output_ppt_path), ())
        print(f"UNO: 翻译应用完成，已保存到 {output_ppt_path}")

    finally:
        if presentation:
            presentation.close(True)


# --- 脚本入口 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UNO PPT Formatter")
    parser.add_argument('--action', required=True, choices=['extract', 'apply'], help="执行的操作")
    parser.add_argument('--input-ppt', required=True, help="输入PPT文件路径")
    parser.add_argument('--output-ppt', help="输出PPT文件路径 (仅用于 apply)")
    parser.add_argument('--json-path', required=True, help="用于数据交换的JSON文件路径")
    parser.add_argument('--pages', nargs='+', type=int, help="要处理的页面索引(从0开始，仅用于 extract)")

    args = parser.parse_args()

    if args.action == 'extract':
        if not args.pages:
            print("错误: extract 操作需要 --pages 参数。", file=sys.stderr)
            sys.exit(1)
        extract_formatting(args.input_ppt, args.json_path, args.pages)
    elif args.action == 'apply':
        if not args.output_ppt:
            print("错误: apply 操作需要 --output-ppt 参数。", file=sys.stderr)
            sys.exit(1)
        apply_translations(args.input_ppt, args.json_path, args.output_ppt)