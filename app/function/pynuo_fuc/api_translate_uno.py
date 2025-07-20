# 请先安装 OpenAI SDK: `pip3 install openai`
'''
api_translate_uno.py
支持段落层级的翻译API模块
'''
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json
import re
from logger_config import get_logger
from openai import OpenAI
import unicodedata
import ast

# 获取日志记录器
logger = get_logger("pyuno")

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
def translate(text, model = "qwen"):
    if model == "qwen":
        logger.info("model参数设置为qwen,使用qwen2.5-72b-instruct模型")
        client = OpenAI(api_key=QWEN_API_KEY, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        used_model = "qwen2.5-72b-instruct"
    elif model == "deepseek":
        logger.info("model参数设置为deepseek,使用deepseek-chat模型")
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")
        used_model = "deepseek-chat"
    else:
        raise ValueError(f"不支持的模型: {model}") 
    response = client.chat.completions.create(
        model = used_model,
        messages=[
            {"role": "system", "content": f"""您是翻译领域的专家。接下来，您将获得一系列文本（包括短语、句子和单词），他们是隶属于同一个PPT的同一页面下的文本框段落的所有文本。
                                              请将每一段文本翻译成专业的中文。
                                              1. 上传的将是一个格式化文本，结构如下：
                                                第1页内容：

                                                【文本框1-段落1】
                                                【文本框1-段落1内的原始文本】

                                                【文本框1-段落2】
                                                【文本框1-段落2内的原始文本】

                                                【文本框2-段落1】
                                                【文本框2-段落1内的原始文本】
                                                 
                                                每一个文本元素都是该PPT页面内一个文本框的一个段落的完整内容，请**保持整体性**，即便出现换行符等特殊符号，也务必完整翻译全文,同时保留这些换行符。
                                              2. 原文中存在形式为[block]的分隔符，该符的作用是区分不同字体格式的文本，请不要对[block]符进行翻译。但是在翻译后的内容中你仍然需要在最后处理时要插入与原文相同数量的[block]符,且插入的位置应该在与原文相同词义的位置，以此作为后续格式处理的标记。
                                                 你需要保证翻译后的内容中，[block]符的个数与原文相同，这也就代表着译前译后拥有相同数量的文本片段，这些文段有不同的字体格式，但一一对应。
                                              3. 不要输出任何不可见字符、控制字符、特殊符号
                                              4. 如果原文出现了中文甚至全文段都是中文，就将中文写在source_language中，且target_language中仍然保留。
                                              5. 输出格式应严格保持输入顺序，一段对应一段，使用如下 JSON 格式输出：
                                              [
                                                  {{
                                                      \"box_index\": 1,
                                                      \"paragraph_index\": 1,
                                                      \"source_language\": \"【文本框1-段落1的原始文本】\",
                                                      \"target_language\": \"【文本框1-段落1的翻译】\"
                                                  }},
                                                  {{
                                                      \"box_index\": 1,
                                                      \"paragraph_index\": 2,
                                                      \"source_language\": \"【文本框1-段落2的原始文本】\",
                                                      \"target_language\": \"【文本框1-段落2的翻译】\"
                                                  }},
                                                  {{
                                                      \"box_index\": 2,
                                                      \"paragraph_index\": 1,
                                                      \"source_language\": \"【文本框2-段落1的原始文本】\",
                                                      \"target_language\": \"【文本框2-段落1的翻译】\"
                                                  }}
                                              ]
                                              **重要：请严格遵守以下翻译规则**：
                                              1. **格式要求**：
                                                  - 对每个文本框段落，输出一个 JSON 对象，格式如下：
                                                  {{
                                                      \"box_index\": 文本框序号,
                                                      \"paragraph_index\": 段落序号,
                                                      \"source_language\": \"原语言文本\",
                                                      \"target_language\": \"译文\"
                                                  }}
                                                  - 按文本框段落顺序在 **同一个 JSON 数组** 内输出
                                                  - **不要输出额外信息、注释或多余文本**。
                                                  - box_index 和 paragraph_index 必须与输入中的【文本框X-段落Y】序号完全对应
                                              现在，请按照上述规则翻译文本"""},
            {"role": "user", "content": text}
        ],
        stream=False
    )
    return response.choices[0].message.content

def clean_translation_text(text: str) -> str:
    """
    清理翻译文本中的不可见字符和特殊控制字符
    """
    if not text:
        return text

    # 移除常见控制字符
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)
    # 移除零宽字符、不可见空格等
    invisible_chars = [
        '\u200b',  # 零宽空格
        '\u200c',  # 零宽非连接符
        '\u200d',  # 零宽连接符
        '\u200e',  # 从左到右标记
        '\u200f',  # 从右到左标记
        '\u202a',  # 从左到右嵌入
        '\u202b',  # 从右到左嵌入
        '\u202c',  # 嵌入结束
        '\u202d',  # 从左到右覆盖
        '\u202e',  # 从右到左覆盖
        '\ufeff',  # BOM
    ]
    for ch in invisible_chars:
        text = text.replace(ch, '')

    # 还可以用unicodedata过滤所有类别为"Cf"的字符
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')

    return text.strip()

def parse_formatted_text_async(text: str):
    """
    异步解析格式化文本（JSON）

    Args:
        text: 格式化文本

    Returns:
        解析结果
    """
    logger.debug(f"原始待解析文本: {repr(text)}")
    cleaned_text = clean_translation_text(text)
    logger.debug(f"清理后待解析文本: {repr(cleaned_text)}")
    
    # 先尝试直接用json解析
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logger.warning(f"初次解析 JSON 失败，尝试 ast.literal_eval: {e}")
        try:
            result = ast.literal_eval(cleaned_text)
            logger.info("使用 ast.literal_eval 成功解析")
            return result
        except Exception as e2:
            logger.warning(f"ast.literal_eval 解析失败，尝试正则提取: {e2}")
            # 尝试正则提取JSON主体
            json_block = extract_json_block(cleaned_text)
            try:
                return json.loads(json_block)
            except Exception as e3:
                logger.warning(f"正则提取后仍失败，尝试大模型修复: {e3}")
                # 调用大模型修复
                fixed_text = clean_translation_text(re_parse_formatted_text_async(json_block))
                logger.debug(f"修复后待解析文本: {repr(fixed_text)}")
                return json.loads(fixed_text)

def re_parse_formatted_text_async(text: str):
    """
    同步重新解析格式化文本，修复可能的格式错误
    Args:
        text: 格式可能错误的文本
    Returns:
        修复后的文本
    """
    try:
        client = OpenAI(api_key=QWEN_API_KEY, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        response = client.chat.completions.create(
            model="qwen2.5-72b-instruct",
            messages=[
                {"role": "system", "content": """
                 你是一个 JSON 解析和修复专家。你的任务是修复一段 **可能存在格式错误的 JSON**，并输出一个 **严格符合 JSON 标准** 的 **格式正确的 JSON**。

### **规则要求：**
1. **确保 JSON 格式正确**：修复任何可能的语法错误，如缺少引号、逗号、括号不匹配等。
2. **保持原始结构和数据**：除非必要，尽量不修改原始数据内容，仅修复格式问题。
3. **正确处理数据类型**：
   - **字符串** 应该使用 **双引号 `"`** 包裹，而不是单引号 `'`。
   - **数字** 应保持原始数值，不要转换为字符串。
   - **布尔值**（`true` / `false`）和 **null** 必须符合 JSON 规范，不要误修改。
4. **不输出额外文本**：
   - **仅输出修复后的 JSON**，不要添加解释、注释或额外的说明文本。
   """},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=8000
        )
        result = response.choices[0].message.content
        logger.info(f"JSON修复成功")
        return result
    except Exception as e:
        logger.error(f"修复JSON格式失败，返回原文: {str(e)}")
        return text

def separate_translate_text(text_translate):
    """
    解析翻译后的JSON文本，提取所有target_language字段，并按文本框段落索引组织
    """
    # 对json文本进行简单的字符过滤
    text_clean = clean_translation_text(text_translate)
    
    # 解析JSON
    try:
        data = parse_formatted_text_async(text_clean)
    except Exception as e:
        raise ValueError(f"翻译结果不是合法JSON: {e}\n{text_translate}")
    
    # 处理新的JSON格式：带box_index和paragraph_index的数组
    if isinstance(data, list):
        # 新格式：带box_index和paragraph_index的数组
        box_paragraph_translations = {}
        
        for item in data:
            box_index = item.get("box_index")
            paragraph_index = item.get("paragraph_index")
            target_language = item.get("target_language", "")
            
            if box_index is not None and paragraph_index is not None:
                # 创建复合键：box_index_paragraph_index
                key = f"{box_index}_{paragraph_index}"
                
                # 将翻译文本按[block]分割成片段
                fragments = [seg.strip() for seg in target_language.split('[block]') if seg.strip()]
                box_paragraph_translations[key] = fragments
                
                logger.debug(f"解析文本框 {box_index} 段落 {paragraph_index}: {len(fragments)} 个片段")
        
        logger.info(f"解析到 {len(box_paragraph_translations)} 个文本框段落的翻译结果")
        return box_paragraph_translations
        
    elif isinstance(data, dict):
        # 兼容旧格式：单个对象（为了向后兼容）
        target_language = data.get("target_language", "")
        fragments = [seg.strip() for seg in target_language.split('[block]') if seg.strip()]
        
        # 假设是第一个文本框的第一个段落
        return {"1_1": fragments}
    
    else:
        raise ValueError("翻译结果JSON格式不正确")

def format_page_text_for_translation(text_boxes_data, page_index):
    """
    格式化指定页面的文本用于翻译API调用（支持段落层级）
    
    Args:
        text_boxes_data: 文本框段落数据列表
        page_index: 要处理的页面索引
        
    Returns:
        str: 格式化后的页面文本内容
    """
    # 过滤出指定页面的文本框段落数据
    page_box_paragraphs = [box_para for box_para in text_boxes_data if box_para['page_index'] == page_index]
    
    if not page_box_paragraphs:
        return ""
    
    formatted_text = f"第{page_index + 1}页内容：\n\n"
    
    # 按文本框和段落组织数据
    box_paragraphs_dict = {}
    for box_para in page_box_paragraphs:
        box_index = box_para['box_index']
        paragraph_index = box_para['paragraph_index']
        
        if box_index not in box_paragraphs_dict:
            box_paragraphs_dict[box_index] = {}
        
        box_paragraphs_dict[box_index][paragraph_index] = box_para
    
    # 按文本框索引排序输出
    for box_index in sorted(box_paragraphs_dict.keys()):
        paragraphs_dict = box_paragraphs_dict[box_index]
        
        # 按段落索引排序输出
        for paragraph_index in sorted(paragraphs_dict.keys()):
            box_para = paragraphs_dict[paragraph_index]
            
            # 使用1-based索引显示
            formatted_text += f"【文本框{box_index + 1}-段落{paragraph_index + 1}】\n"
            formatted_text += f"{box_para['combined_text']}\n\n"
    
    logger.debug(f"第 {page_index + 1} 页格式化了 {len(page_box_paragraphs)} 个文本框段落")
    return formatted_text.strip()

def translate_pages_by_page(text_boxes_data, progress_callback,source_language='en', target_language='zh',model='qwen',):
    """
    按页翻译文本内容，每页调用一次翻译API（支持段落层级）
    
    Args:
        text_boxes_data: 文本框段落数据列表
        source_language: 源语言
        target_language: 目标语言
        
    Returns:
        dict: 翻译结果，格式为 {page_index: translated_content}
    """
    logger.info(f"开始按页翻译（段落层级），共 {len(text_boxes_data)} 个文本框段落")
    
    # 获取所有页面索引
    page_indices = set(box_para['page_index'] for box_para in text_boxes_data)
    logger.info(f"需要翻译的页面: {sorted(page_indices)}")
    
    # 显示每页的文本框段落统计
    for page_index in sorted(page_indices):
        page_box_paragraphs = [bp for bp in text_boxes_data if bp['page_index'] == page_index]
        logger.info(f"第 {page_index + 1} 页有 {len(page_box_paragraphs)} 个文本框段落")
        
        # 显示详细的文本框段落分布
        box_para_dist = {}
        for bp in page_box_paragraphs:
            box_idx = bp['box_index']
            if box_idx not in box_para_dist:
                box_para_dist[box_idx] = 0
            box_para_dist[box_idx] += 1
        
        for box_idx in sorted(box_para_dist.keys()):
            logger.info(f"  文本框 {box_idx + 1}: {box_para_dist[box_idx]} 个段落")
    
    translation_results = {}
    if progress_callback:
        progress_callback(0, len(page_indices))
    for page_index in sorted(page_indices):
        logger.info(f"正在处理第 {page_index + 1} 页...")
        if progress_callback:
            progress_callback(page_index + 1, len(page_indices))
        # 生成该页的格式化文本
        page_content = format_page_text_for_translation(text_boxes_data, page_index)
        
        if not page_content:
            logger.warning(f"第 {page_index + 1} 页没有文本内容，跳过")
            continue
        
        logger.info(f"第 {page_index + 1} 页格式化文本:")
        logger.info("-" * 40)
        # logger.info(page_content)
        logger.info("-" * 40)
        
        try:
            # 调用翻译API
            logger.info(f"正在调用翻译API翻译第 {page_index + 1} 页...")
            translated_result = translate(page_content,model)          
            logger.info(f"第 {page_index + 1} 页翻译完成")
            logger.info("翻译结果:")
            logger.info("-" * 40)
            # logger.info(translated_result)
            logger.info("-" * 40)
            
            # 解析翻译结果
            translated_fragments = separate_translate_text(translated_result)
            
            # 存储翻译结果 - 现在translated_fragments是按文本框段落索引组织的
            page_box_paragraphs = [bp for bp in text_boxes_data if bp['page_index'] == page_index]
            
            translation_results[page_index] = {
                'original_content': page_content,
                'translated_json': translated_result,
                'translated_fragments': translated_fragments,  # 现在是 {box_paragraph_key: fragments}
                'box_paragraph_count': len(page_box_paragraphs),
                'box_count': len(set(bp['box_index'] for bp in page_box_paragraphs))  # 实际的文本框数量
            }
            
            logger.info(f"第 {page_index + 1} 页翻译完成，得到 {len(translated_fragments)} 个文本框段落的翻译")
            
            # 显示翻译结果的键值对应关系
            logger.info("翻译结果键值映射:")
            for key, fragments in translated_fragments.items():
                logger.info(f"  {key}: {len(fragments)} 个片段")
            
        except Exception as e:
            logger.error(f"翻译第 {page_index + 1} 页时出错: {e}", exc_info=True)
            # 如果翻译失败，记录错误信息
            page_box_paragraphs = [bp for bp in text_boxes_data if bp['page_index'] == page_index]
            translation_results[page_index] = {
                'original_content': page_content,
                'error': str(e),
                'translated_fragments': {},
                'box_paragraph_count': len(page_box_paragraphs),
                'box_count': len(set(bp['box_index'] for bp in page_box_paragraphs))
            }
    
    logger.info(f"按页翻译完成，共处理 {len(translation_results)} 页")
    
    # 显示统计信息
    successful_pages = len([r for r in translation_results.values() if 'error' not in r])
    failed_pages = len([r for r in translation_results.values() if 'error' in r])
    total_box_paragraphs_translated = sum(len(r.get('translated_fragments', {})) for r in translation_results.values())
    total_boxes_translated = sum(r.get('box_count', 0) for r in translation_results.values())
    
    logger.info("翻译统计:")
    logger.info(f"  - 成功翻译页数: {successful_pages}")
    logger.info(f"  - 翻译失败页数: {failed_pages}")
    logger.info(f"  - 总翻译文本框数: {total_boxes_translated}")
    logger.info(f"  - 总翻译文本框段落数: {total_box_paragraphs_translated}")
    
    return translation_results

def extract_json_block(text):
    """
    尝试提取最外层的[]或{}包裹的内容
    """
    import re
    match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1)
    return text  # 如果没找到，返回原文

def validate_translation_result(translation_results, text_boxes_data):
    """
    验证翻译结果的完整性和正确性
    
    Args:
        translation_results: 翻译结果
        text_boxes_data: 原始文本框段落数据
        
    Returns:
        dict: 验证结果统计
    """
    logger = get_logger("pyuno")
    logger.info("开始验证翻译结果...")
    
    validation_stats = {
        'total_expected_box_paragraphs': len(text_boxes_data),
        'total_translated_box_paragraphs': 0,
        'missing_translations': [],
        'extra_translations': [],
        'fragment_count_mismatches': [],
        'pages_processed': len(translation_results)
    }
    
    try:
        # 创建预期的文本框段落映射
        expected_box_paragraphs = {}
        for box_para in text_boxes_data:
            page_idx = box_para['page_index']
            box_idx = box_para['box_index']
            para_idx = box_para['paragraph_index']
            key = f"{box_idx + 1}_{para_idx + 1}"  # 转为1-based
            
            if page_idx not in expected_box_paragraphs:
                expected_box_paragraphs[page_idx] = {}
            
            expected_box_paragraphs[page_idx][key] = {
                'expected_fragments': len(box_para['texts']),
                'box_para_data': box_para
            }
        
        # 验证每页的翻译结果
        for page_idx, translation_result in translation_results.items():
            if 'error' in translation_result:
                logger.warning(f"第 {page_idx + 1} 页翻译失败，跳过验证")
                continue
            
            translated_fragments = translation_result.get('translated_fragments', {})
            expected_for_page = expected_box_paragraphs.get(page_idx, {})
            
            # 检查缺失的翻译
            for expected_key in expected_for_page:
                if expected_key not in translated_fragments:
                    validation_stats['missing_translations'].append(f"页面{page_idx + 1}-{expected_key}")
                else:
                    # 检查片段数量是否匹配
                    expected_count = expected_for_page[expected_key]['expected_fragments']
                    actual_count = len(translated_fragments[expected_key])
                    
                    if expected_count != actual_count:
                        validation_stats['fragment_count_mismatches'].append({
                            'location': f"页面{page_idx + 1}-{expected_key}",
                            'expected': expected_count,
                            'actual': actual_count
                        })
                    
                    validation_stats['total_translated_box_paragraphs'] += 1
            
            # 检查多余的翻译
            for actual_key in translated_fragments:
                if actual_key not in expected_for_page:
                    validation_stats['extra_translations'].append(f"页面{page_idx + 1}-{actual_key}")
        
        # 计算验证统计
        validation_stats['translation_coverage'] = (
            validation_stats['total_translated_box_paragraphs'] / 
            validation_stats['total_expected_box_paragraphs'] * 100
            if validation_stats['total_expected_box_paragraphs'] > 0 else 0
        )
        
        # 记录验证结果
        logger.info("翻译结果验证完成:")
        logger.info(f"  - 预期文本框段落数: {validation_stats['total_expected_box_paragraphs']}")
        logger.info(f"  - 实际翻译文本框段落数: {validation_stats['total_translated_box_paragraphs']}")
        logger.info(f"  - 翻译覆盖率: {validation_stats['translation_coverage']:.2f}%")
        logger.info(f"  - 缺失翻译数: {len(validation_stats['missing_translations'])}")
        logger.info(f"  - 多余翻译数: {len(validation_stats['extra_translations'])}")
        logger.info(f"  - 片段数量不匹配数: {len(validation_stats['fragment_count_mismatches'])}")
        
        # 如果有问题，记录详细信息
        if validation_stats['missing_translations']:
            logger.warning(f"缺失的翻译: {validation_stats['missing_translations']}")
        
        if validation_stats['extra_translations']:
            logger.warning(f"多余的翻译: {validation_stats['extra_translations']}")
        
        if validation_stats['fragment_count_mismatches']:
            logger.warning("片段数量不匹配的情况:")
            for mismatch in validation_stats['fragment_count_mismatches']:
                logger.warning(f"  {mismatch['location']}: 预期 {mismatch['expected']}, 实际 {mismatch['actual']}")
        
        return validation_stats
        
    except Exception as e:
        logger.error(f"验证翻译结果时出错: {e}", exc_info=True)
        return validation_stats

if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("api_translate_uno 模块测试（段落层级支持）")
    print("=" * 60)
    
    logger = get_logger("pyuno.test")
    logger.info("api_translate_uno 模块加载成功")
    
    # 创建模拟的文本框段落数据进行测试
    mock_text_boxes_data = [
        {
            'page_index': 0,
            'box_index': 0,
            'box_id': 'textbox_0',
            'paragraph_index': 0,
            'paragraph_id': 'para_0_0',
            'texts': ['Hello', 'world'],
            'combined_text': 'Hello[block]world'
        },
        {
            'page_index': 0,
            'box_index': 0,
            'box_id': 'textbox_0',
            'paragraph_index': 1,
            'paragraph_id': 'para_0_1',
            'texts': ['This is', 'a test'],
            'combined_text': 'This is[block]a test'
        }
    ]
    
    try:
        # 测试格式化函数
        formatted_text = format_page_text_for_translation(mock_text_boxes_data, 0)
        logger.info("格式化测试成功:")
        logger.info(formatted_text)
        
        # 测试翻译结果解析（模拟）
        mock_translation_result = '''[
            {
                "box_index": 1,
                "paragraph_index": 1,
                "source_language": "Hello[block]world",
                "target_language": "你好[block]世界"
            },
            {
                "box_index": 1,
                "paragraph_index": 2,
                "source_language": "This is[block]a test",
                "target_language": "这是[block]一个测试"
            }
        ]'''
        
        translated_fragments = separate_translate_text(mock_translation_result)
        logger.info("翻译结果解析测试成功:")
        for key, fragments in translated_fragments.items():
            logger.info(f"  {key}: {fragments}")
        
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
    
    print("=" * 60)
