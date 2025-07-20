'''
pyuno_controller.py
pyuno的总控制器，负责调用pyuno的各个模块，并进行相应的处理（支持段落层级）
'''
import subprocess
import json
import os   
import tempfile
from typing import List, Dict
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from logger_config import setup_default_logging, get_logger, log_function_call, log_execution_time
from ppt_data_utils import extract_texts_for_translation, call_translation_api, map_translation_results_back, save_translated_ppt_data

LIBREOFFICE_PYTHON = os.getenv("LIBREOFFICE_PYTHON")
SOFFICE_PATH = os.getenv("SOFFICE_PATH")

import psutil
import time

def check_soffice_alive():
    for proc in psutil.process_iter(['name']):
        name = proc.info['name']
        if name and 'soffice' in name.lower():
            return True
    return False

def ensure_soffice_running():
    """
    检查soffice服务是否存活，如未运行则自动启动。
    """
    logger = get_logger("pyuno.main")
    if check_soffice_alive():
        logger.info("检测到LibreOffice headless 服务已在运行，无需重启。")
        return
    logger.warning("未检测到LibreOffice headless 服务，尝试自动启动...")
    soffice_path = SOFFICE_PATH or "C:/Program Files/LibreOffice/program/soffice.exe"
    soffice_cmd = [
        soffice_path,
        '--headless',
        '--accept=socket,host=localhost,port=2002;urp;'
    ]
    try:
        # 启动soffice服务，使用DETACHED_PROCESS避免阻塞
        subprocess.Popen(
            soffice_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logger.info("已尝试启动LibreOffice headless 服务，等待服务就绪...")
        # 等待几秒钟，确保服务启动
        for i in range(10):
            if check_soffice_alive():
                logger.info("LibreOffice headless 服务启动成功！")
                return
            time.sleep(1)
        logger.error("自动启动LibreOffice headless 服务失败，请手动检查！")
    except Exception as e:
        logger.error(f"启动soffice服务时出错: {e}", exc_info=True)

# 设置日志记录器
logger = setup_default_logging()

def run_load_ppt_subprocess(ppt_path):
    """
    使用子进程运行load_ppt功能
    """
    start_time = datetime.now()
    log_function_call(logger, "run_load_ppt_subprocess", ppt_path=ppt_path)
    
    # 创建temp目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(current_dir, "temp")
    
    # 确保temp目录存在
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        logger.info(f"创建temp目录: {temp_dir}")
    
    # 生成唯一的输出文件名
    import uuid
    output_filename = f"load_ppt_result_{uuid.uuid4().hex[:8]}.json"
    output_file = os.path.join(temp_dir, output_filename)
    
    logger.info(f"使用temp目录: {temp_dir}")
    logger.info(f"输出文件路径: {output_file}")
    
    # 获取当前脚本所在目录，构建load_ppt.py路径
    load_ppt_script = os.path.join(current_dir, "load_ppt.py")
    
    logger.debug(f"当前工作目录: {current_dir}")
    logger.debug(f"load_ppt脚本路径: {load_ppt_script}")
    
    # 检查脚本文件是否存在
    if not os.path.exists(load_ppt_script):
        logger.error(f"找不到load_ppt.py脚本: {load_ppt_script}")
        return None
    
    # 使用LibreOffice自带的Python解释器
    libreoffice_python = LIBREOFFICE_PYTHON or "C:/Program Files/LibreOffice/program/python.exe"
    
    # 检查Python解释器是否存在
    if not os.path.exists(libreoffice_python):
        logger.error(f"找不到LibreOffice Python解释器: {libreoffice_python}")
        logger.error("请设置环境变量 LIBREOFFICE_PYTHON 或确认LibreOffice安装路径")
        return None
    
    # 构建命令
    cmd = [
        libreoffice_python, load_ppt_script,
        "--input", ppt_path,
        "--output", output_file
    ]
    
    logger.info(f"启动子进程命令: {' '.join(cmd)}")
    logger.info(f"工作目录: {current_dir}")
    logger.info(f"使用Python解释器: {libreoffice_python}")
    logger.info(f"临时目录: {temp_dir}")
    
    try:
        # 运行子进程，设置环境变量确保UTF-8编码
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        logger.debug("开始执行子进程...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',  # 明确指定编码
            errors='replace',  # 处理无法解码的字符
            cwd=current_dir,
            env=env,
            timeout=180  # 增加超时时间到180秒
        )
        
        if result.returncode == 0:
            logger.info("子进程执行成功")
            logger.debug(f"子进程标准输出: {result.stdout}")
            logger.info(f"子进程返回码: {result.returncode}")
            logger.info(f"stdout:\n{result.stdout}")
            logger.info(f"stderr:\n{result.stderr}")

            # 读取结果
            if os.path.exists(output_file):
                logger.info(f"找到输出文件: {output_file}")
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 新的统计信息结构
                stats = data.get('statistics', {})
                total_pages = stats.get('total_pages', 0)
                total_boxes = stats.get('total_boxes', 0)
                total_paragraphs = stats.get('total_paragraphs', 0)
                total_fragments = stats.get('total_fragments', 0)
                
                logger.info(f"成功读取PPT内容，共 {total_pages} 页，{total_boxes} 个文本框，{total_paragraphs} 个段落，{total_fragments} 个文本片段")
                
                log_execution_time(logger, "run_load_ppt_subprocess", start_time)
                return data
            else:
                logger.error(f"未找到输出文件: {output_file}")
                return None
        else:
            logger.error(f"子进程执行失败，返回码: {result.returncode}")
            logger.error(f"子进程错误输出: {result.stderr}")
            logger.debug(f"子进程标准输出: {result.stdout}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("子进程超时（180秒）")
        logger.error("可能的原因：")
        logger.error("1. LibreOffice监听服务未启动")
        logger.error("2. PPT文件过大或复杂")
        logger.error("3. 系统资源不足")
        logger.error("\n请确保LibreOffice服务正在运行：")
        logger.error("soffice --headless --accept=\"socket,host=localhost,port=2002;urp;StarOffice.ComponentContext\"")
        return None
    except Exception as e:
        logger.error(f"运行子进程时出错: {str(e)}", exc_info=True)
        return None
    finally:
        # 清理临时文件（可选，保留用于调试）
        # 如果需要保留文件用于调试，可以注释掉下面的清理代码
        try:
            if os.path.exists(output_file):
                os.remove(output_file)
                logger.info(f"已删除临时文件: {output_file}")
        except Exception as e:
            logger.error(f"删除临时文件失败: {str(e)}")
        pass

def run_change_ppt_subprocess(ppt_path, save_path, translated_json_path, mode='paragraph'):
    """
    使用子进程运行edit_ppt功能，将译文写入PPT
    """
    start_time = datetime.now()
    log_function_call(logger, "run_change_ppt_subprocess", ppt_path=ppt_path, save_path=save_path, translated_json_path=translated_json_path, mode=mode)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = os.path.join(current_dir, "temp")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        logger.info(f"创建temp目录: {temp_dir}")
    
    edit_ppt_script = os.path.join(current_dir, "edit_ppt.py")
    if not os.path.exists(edit_ppt_script):
        logger.error(f"找不到edit_ppt.py脚本: {edit_ppt_script}")
        return None
    
    libreoffice_python = LIBREOFFICE_PYTHON or "C:/Program Files/LibreOffice/program/python.exe"
    if not os.path.exists(libreoffice_python):
        logger.error(f"找不到LibreOffice Python解释器: {libreoffice_python}")
        logger.error("请设置环境变量 LIBREOFFICE_PYTHON 或确认LibreOffice安装路径")
        return None
    
    cmd = [
        libreoffice_python, edit_ppt_script,
        "--input", ppt_path,
        "--output", save_path,
        "--json", translated_json_path,
        "--mode", mode
    ]
    logger.info(f"启动子进程命令: {' '.join(cmd)}")
    logger.info(f"工作目录: {current_dir}")
    logger.info(f"使用Python解释器: {libreoffice_python}")
    logger.info(f"临时目录: {temp_dir}")
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        logger.debug("开始执行子进程...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=current_dir,
            env=env,
            timeout=180
        )
        if result.returncode == 0:
            logger.info("子进程执行成功")
            logger.debug(f"子进程标准输出: {result.stdout}")
            logger.info(f"已生成翻译PPT: {save_path}")
            log_execution_time(logger, "run_change_ppt_subprocess", start_time)
            return save_path
        else:
            logger.error(f"子进程执行失败，返回码: {result.returncode}")
            logger.error(f"子进程错误输出: {result.stderr}")
            logger.debug(f"子进程标准输出: {result.stdout}")
            return None
    except subprocess.TimeoutExpired:
        logger.error("子进程超时（180秒）")
        logger.error("请检查LibreOffice服务和PPT文件大小/复杂度")
        return None
    except Exception as e:
        logger.error(f"运行子进程时出错: {str(e)}", exc_info=True)
        return None
    finally:
        try:
            if os.path.exists(translated_json_path):
                os.remove(translated_json_path)
                logger.info(f"已删除临时文件: {translated_json_path}")
        except Exception as e:
            logger.error(f"删除临时文件失败: {str(e)}")
        pass

def pyuno_controller(presentation_path: str,
                                   stop_words_list: List[str],
                                   custom_translations: Dict[str, str],
                                   select_page: List[int],
                                   source_language: str,
                                   target_language: str,
                                   bilingual_translation: str,
                                   progress_callback=None,
                                   model:str='qwen'):
    """
    主控制器函数（支持段落层级）
    
    参数说明：
    - bilingual_translation: 翻译模式，支持以下值：
      * "replace": 替换原文
      * "append": 在末尾追加译文
      * "paragraph": 逐段翻译，在每个段落下方插入对应译文
      * "bilingual": 双语模式（默认）
    """
    start_time = datetime.now()
    
    # ====== 新增：确保soffice服务存活，如未运行则自动启动 ======
    ensure_soffice_running()

    # 记录函数调用参数
    log_function_call(logger, "pyuno_controller", 
                     presentation_path=presentation_path,
                     stop_words_list=stop_words_list,
                     custom_translations=custom_translations,
                     select_page=select_page,
                     source_language=source_language,
                     target_language=target_language,
                     bilingual_translation=bilingual_translation,
                     model=model)
    
    logger.info(f"开始处理PPT（段落层级翻译支持）: {presentation_path}")
    logger.info(f"翻译模式: {bilingual_translation}")
    logger.info("新功能：支持段落级别的精确翻译和格式保持")
    
    # 检查PPT文件是否存在
    if not os.path.exists(presentation_path):
        logger.error(f"PPT文件不存在: {presentation_path}")
        return None
    
    # 检查文件大小
    file_size = os.path.getsize(presentation_path)
    logger.info(f"PPT文件大小: {file_size / (1024*1024):.2f} MB")
    
    # 第一步：使用子进程加载PPT
    logger.info("开始第一步：加载PPT内容（段落层级）")
    ppt_data = run_load_ppt_subprocess(presentation_path)
    
    if not ppt_data:
        logger.error("无法加载PPT内容，请检查LibreOffice服务是否正在运行")
        return None
    
    logger.info("PPT加载完成，准备进行第二步处理...")
    
    # 第二步：翻译PPT内容
    logger.info("开始第二步：翻译PPT内容（段落层级）")
    try:
        # 提取文本片段（支持段落层级）
        text_boxes_data, fragment_mapping = extract_texts_for_translation(ppt_data)
        
        if not text_boxes_data:
            logger.warning("没有找到需要翻译的文本框段落")
            return ppt_data
        
        # 显示准备输入到API的内容
        logger.info("=" * 60)
        logger.info("准备输入到翻译API的内容（按文本框段落分组）:")
        logger.info("=" * 60)
        
        # 显示每个文本框段落的内容
        for i, box_para_data in enumerate(text_boxes_data):
            logger.info(f"文本框段落 {i+1} (页面{box_para_data['page_index']+1}, {box_para_data['box_id']}, {box_para_data['paragraph_id']}):")
            logger.info(f"  包含 {len(box_para_data['texts'])} 个文本片段:")
            for j, text in enumerate(box_para_data['texts']):
                logger.info(f"    片段 {j+1}: '{text}'")
            logger.info(f"  段落合并文本: '{box_para_data['combined_text']}'")
            logger.info("-" * 40)
        
        # 显示每个文本框段落的统计信息
        logger.info("=" * 60)
        logger.info("各文本框段落统计信息:")
        logger.info("=" * 60)
        for i, box_para_data in enumerate(text_boxes_data):
            text_length = len(box_para_data['combined_text'])
            logger.info(f"文本框段落 {i+1}: {len(box_para_data['texts'])} 个片段, {text_length} 字符")
        
        # 按页调用翻译API
        logger.info("=" * 60)
        logger.info("开始按页调用翻译API（段落层级）...")
        
        try:
            from api_translate_uno import translate_pages_by_page, validate_translation_result
            translation_results = translate_pages_by_page(text_boxes_data,progress_callback, source_language, target_language,model)
            
            logger.info(f"翻译完成，共处理 {len(translation_results)} 页")
            
            # 验证翻译结果
            validation_stats = validate_translation_result(translation_results, text_boxes_data)
            logger.info(f"翻译结果验证完成，覆盖率: {validation_stats['translation_coverage']:.2f}%")
            
            # 显示翻译结果
            logger.info("=" * 60)
            logger.info("翻译结果验证:")
            logger.info("=" * 60)
            
            for page_index, result in translation_results.items():
                logger.info(f"第 {page_index + 1} 页翻译结果:")
                logger.info(f"  文本框段落数量: {result['box_paragraph_count']}")
                logger.info(f"  实际文本框数量: {result['box_count']}")
                
                if 'error' in result:
                    logger.error(f"  翻译失败: {result['error']}")
                else:
                    box_paragraph_translations = result['translated_fragments']
                    logger.info(f"  翻译文本框段落数: {len(box_paragraph_translations)}")
                    # logger.info(f"  翻译JSON: {result['translated_json']}")
                    
                    # 显示每个文本框段落的翻译结果
                    for box_para_key, fragments in box_paragraph_translations.items():
                        logger.info(f"    文本框段落 {box_para_key}:")
                        # for i, fragment in enumerate(fragments):
                        #     logger.info(f"      片段 {i+1}: '{fragment}'")
                
                logger.info("-" * 40)
            
            # 显示完整的translation_results结构
            logger.info("=" * 60)
            logger.info("完整的translation_results结构:")
            logger.info("=" * 60)
            # logger.info(json.dumps(translation_results, ensure_ascii=False, indent=2))
            logger.info("=" * 60)
            
            # 保存翻译结果到temp_result目录
            logger.info("=" * 60)
            logger.info("保存翻译结果...")
            logger.info("=" * 60)
            
            # 创建temp_result目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            temp_result_dir = os.path.join(current_dir, "temp_result")
            
            if not os.path.exists(temp_result_dir):
                os.makedirs(temp_result_dir)
                logger.info(f"创建temp_result目录: {temp_result_dir}")
            
            # 生成翻译结果文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_filename = f"translated_result_paragraphs_{timestamp}.json"
            result_file_path = os.path.join(temp_result_dir, result_filename)
            
            logger.info("第二步完成（按页翻译API调用完成，结果已保存）")
            
            # 第三步：将翻译结果映射回原PPT数据结构
            logger.info("=" * 60)
            logger.info("开始第三步：映射翻译结果回原PPT数据结构（段落层级）...")
            logger.info("=" * 60)
            
            try:
                translated_ppt_data = map_translation_results_back(ppt_data, translation_results, text_boxes_data)
                
                logger.info("翻译结果映射完成")
                # logger.info(f"翻译元数据: {translated_ppt_data.get('translation_metadata', {})}")
                
                # 保存包含翻译的完整PPT数据
                logger.info("=" * 60)
                logger.info("保存包含翻译的完整PPT数据...")
                logger.info("=" * 60)
                
                # 生成包含翻译的PPT数据文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ppt_with_translation_filename = f"ppt_with_translation_paragraphs_{timestamp}.json"
                ppt_with_translation_path = os.path.join(temp_result_dir, ppt_with_translation_filename)
                
                try:
                    with open(ppt_with_translation_path, 'w', encoding='utf-8') as f:
                        json.dump(translated_ppt_data, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"包含翻译的PPT数据已保存到: {ppt_with_translation_path}")
                    
                except Exception as e:
                    logger.error(f"保存包含翻译的PPT数据时出错: {e}", exc_info=True)
                
                logger.info("第三步完成（翻译结果映射完成，完整PPT数据已保存）")
                
                # 第四步：生成翻译后的PPT文件
                logger.info("=" * 60)
                logger.info("开始第四步：生成翻译后的PPT文件...")
                logger.info("=" * 60)
                
                try:
                    # 生成输出PPT文件路径
                    input_dir = os.path.dirname(presentation_path)
                    input_filename = os.path.splitext(os.path.basename(presentation_path))[0]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"{input_filename}_translated_paragraphs_{timestamp}.odp"
                    output_pptx_path = os.path.join(input_dir, output_filename)
                    
                    logger.info(f"输入PPT路径: {presentation_path}")
                    logger.info(f"输出PPT路径: {output_pptx_path}")
                    logger.info(f"翻译JSON路径: {ppt_with_translation_path}")
                    logger.info(f"翻译模式: {bilingual_translation}")
                    
                    # 调用子进程生成翻译后的PPT
                    result_pptx_path = run_change_ppt_subprocess(
                        ppt_path=presentation_path,
                        save_path=output_pptx_path,
                        translated_json_path=ppt_with_translation_path,
                        # TODO: 需要修改为bilingual_translation,模式选择尚未完善，写完了记得改。
                        mode="paragraph"
                    )

                    # ====== 新增：检测libreoffice服务是否存活 ======
                    alive = check_soffice_alive()
                    logger.info(f"第二次测试LibreOffice headless 服务状态，在调用修改ppt后: {alive}")
                    if alive:
                        logger.info("LibreOffice headless 服务仍在运行（soffice进程存活）")
                    else:
                        logger.warning("LibreOffice headless 服务已关闭（未检测到soffice进程）")

                    # 获取项目根目录（load_ppt.py 往上退三层）
                    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                    result_pptx_path_abs = os.path.abspath(os.path.join(project_root, result_pptx_path))
                    if not os.path.exists(result_pptx_path_abs):
                        logger.error(f"输入文件不存在: {result_pptx_path_abs}")
                        return None
                    
                    if result_pptx_path_abs:
                        logger.info("=" * 60)
                        logger.info("第四步完成：翻译PPT文件生成成功！")
                        logger.info("=" * 60)
                        logger.info(f"翻译后的PPT文件: {result_pptx_path_abs}")
                        logger.info(f"文件大小: {os.path.getsize(result_pptx_path_abs) / (1024*1024):.2f} MB")
                        logger.info("=" * 60)
                        # ====== ODP转PPTX ======
                        pptx_path = convert_odp_to_pptx(result_pptx_path_abs)
                        if pptx_path:
                            logger.info(f"ODP转PPTX成功，最终PPTX文件: {pptx_path}")
                            logger.info(f"PPTX文件大小: {os.path.getsize(pptx_path) / (1024*1024):.2f} MB")
                        else:
                            logger.error("ODP转PPTX失败，请检查LibreOffice命令行环境")
                            return None
                        # ====== 删除中间ODP文件 ======
                        try:
                            os.remove(result_pptx_path_abs)
                            logger.info(f"已删除中间ODP文件: {result_pptx_path_abs}")
                        except Exception as e:
                            logger.warning(f"删除ODP文件失败: {e}")
                        
                        # ====== 记录处理结果统计（段落层级） ======
                        stats = ppt_data.get('statistics', {})
                        total_pages = stats.get('total_pages', 0)
                        total_boxes = stats.get('total_boxes', 0)
                        total_paragraphs = stats.get('total_paragraphs', 0)
                        total_fragments = stats.get('total_fragments', 0)
                        
                        # ====== 计算翻译统计 ======
                        successful_translations = 0
                        total_translated_box_paragraphs = 0
                        if 'translation_results' in locals():
                            successful_translations = len([r for r in translation_results.values() if 'error' not in r])
                            total_translated_box_paragraphs = sum(len(r.get('translated_fragments', {})) for r in translation_results.values())
                        
                        logger.info(f"处理完成统计（段落层级）:")
                        logger.info(f"  - 总页数: {total_pages}")
                        logger.info(f"  - 总文本框数: {total_boxes}")
                        logger.info(f"  - 总段落数: {total_paragraphs}")
                        logger.info(f"  - 总文本片段数: {total_fragments}")
                        logger.info(f"  - 有内容的文本框段落数: {len(text_boxes_data)}")
                        logger.info(f"  - 成功翻译页数: {successful_translations}")
                        logger.info(f"  - 翻译文本框段落数: {total_translated_box_paragraphs}")
                        
                        log_execution_time(logger, "pyuno_controller", start_time)

                        # ====== 新增：检测libreoffice服务是否存活 ======
                        alive = check_soffice_alive()
                        logger.info(f"第三次测试LibreOffice headless 服务状态，在返回最终PPTX路径后: {alive}")
                        if alive:
                            logger.info("LibreOffice headless 服务仍在运行（soffice进程存活）")
                        else:
                            logger.warning("LibreOffice headless 服务已关闭（未检测到soffice进程）")
                        
                        # ====== 返回最终PPTX路径 ======
                        return pptx_path
                    else:
                        logger.error("第四步失败：生成翻译PPT文件失败")
                        return None
                
                except Exception as e:
                    logger.error(f"第四步执行出错: {e}", exc_info=True)
                    logger.error("生成翻译PPT文件失败")
                    return None
            
            except Exception as e:
                logger.error(f"映射翻译结果时出错: {e}", exc_info=True)
                logger.info("映射失败，使用原始PPT数据")
                translated_ppt_data = ppt_data
            
        except Exception as e:
            logger.error(f"调用翻译API时出错: {e}", exc_info=True)
            logger.info("翻译失败，跳过翻译步骤")
        
        
    except Exception as e:
        logger.error(f"翻译过程中出错: {e}", exc_info=True)
        logger.error("翻译失败，返回None")
        return None

def convert_odp_to_pptx(odp_path, output_dir=None):
    """
    使用LibreOffice命令行将ODP文件转换为PPTX文件
    :param odp_path: 输入的ODP文件路径
    :param output_dir: 输出目录（默认为ODP文件所在目录）
    :return: 转换后PPTX文件路径，失败返回None
    """
    import shutil
    import time

    soffice_path = SOFFICE_PATH or "C:/Program Files/LibreOffice/program/soffice.exe"
    if not os.path.exists(soffice_path):
        logger.error(f"找不到LibreOffice soffice.exe: {soffice_path}")
        logger.error("请设置环境变量 SOFFICE_PATH 或确认LibreOffice安装路径")
        return None

    if not os.path.exists(odp_path):
        logger.error(f"ODP文件不存在: {odp_path}")
        return None

    if output_dir is None:
        output_dir = os.path.dirname(odp_path)

    cmd = [
        soffice_path,
        "--headless",
        "--convert-to", "pptx",
        odp_path,
        "--outdir", output_dir
    ]
    logger.info(f"启动ODP转PPTX命令: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=output_dir,
            timeout=120
        )
        logger.info(f"soffice标准输出: {result.stdout}")
        logger.info(f"soffice错误输出: {result.stderr}")

        if result.returncode == 0:
            # 等待文件生成
            base_name = os.path.splitext(os.path.basename(odp_path))[0]
            pptx_path = os.path.join(output_dir, base_name + ".pptx")
            for _ in range(10):
                if os.path.exists(pptx_path):
                    logger.info(f"转换成功，PPTX文件: {pptx_path}")
                    return pptx_path
                time.sleep(1)
            logger.error("转换命令执行成功，但未找到PPTX文件")
            return None
        else:
            logger.error(f"soffice命令执行失败，返回码: {result.returncode}")
            return None
    except Exception as e:
        logger.error(f"ODP转PPTX过程中出错: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("启动pyuno_controller（段落层级支持）")
    logger.info("=" * 60)
    
    try:
        result = pyuno_controller("F:/pptxTest/pyuno/test_ppt/test.pptx",[],[],[],'en','zh','paragraph')
        if result:
            logger.info("pyuno_controller执行成功")
        else:
            logger.error("pyuno_controller执行失败")
    except Exception as e:
        logger.error(f"pyuno_controller执行异常: {str(e)}", exc_info=True)
