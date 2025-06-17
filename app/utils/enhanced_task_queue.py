"""
增强版翻译任务队列
支持多线程并发处理和异步I/O操作
"""
import asyncio
import threading
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import os
import logging
from concurrent.futures import ThreadPoolExecutor
import uuid
import traceback

from .thread_pool_executor import thread_pool, TaskType, TaskStatus, Task

# 配置日志记录器
logger = logging.getLogger(__name__)

class TranslationTask:
    """翻译任务类，用于存储任务信息"""

    def __init__(self, task_id: str, user_id: int, user_name: str,
                file_path: str, task_type: str = 'ppt_translate',
                source_language: str = 'en', target_language: str = 'zh-cn',
                priority: int = 0, annotation_filename: str = None,
                annotation_json: Dict = None, select_page: List[int] = None,
                bilingual_translation: bool = False, **kwargs):
        """
        初始化翻译任务

        Args:
            task_id: 任务ID
            user_id: 用户ID
            user_name: 用户名
            file_path: 文件路径
            task_type: 任务类型 (ppt_translate, pdf_annotate)
            source_language: 源语言
            target_language: 目标语言
            priority: 优先级
            annotation_filename: 注释文件名
            select_page: 选择的页面列表
            bilingual_translation: 是否双语翻译
            **kwargs: 其他参数
        """
        self.task_id = task_id
        self.user_id = user_id
        self.user_name = user_name
        self.file_path = file_path
        self.task_type = task_type
        self.source_language = source_language
        self.target_language = target_language
        self.priority = priority
        self.annotation_filename = annotation_filename
        self.annotation_json = annotation_json  # 添加注释数据字段
        self.select_page = select_page or []
        self.bilingual_translation = bilingual_translation

        # PDF注释相关参数
        self.annotations = kwargs.get('annotations', [])
        self.output_path = kwargs.get('output_path', '')
        self.ocr_language = kwargs.get('ocr_language', 'chi_sim+eng')

        # 状态信息
        self.status = "waiting"  # waiting, processing, completed, failed, canceled
        self.progress = 0  # 0-100
        self.error = None
        self.start_time = None
        self.end_time = None
        self.retry_count = 0

        # 事件通知
        self.event = threading.Event()

        # 任务状态信息
        self.position = 0
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None

        # 进度信息
        self.current_slide = 0
        self.total_slides = 0

        # 处理结果
        self.result = None

        # 执行此任务的Thread Task对象
        self.thread_task: Optional[Task] = None

        # 详细日志
        self.logs = []
        self.current_stage = "等待中"
        self.current_operation = "排队等待处理"

        # 获取任务专用的日志记录器
        self.logger = logging.getLogger(f"{__name__}.task.{user_id}")
        self.logger.info(f"创建新任务: 用户={user_name}, 文件={os.path.basename(file_path)}")

class EnhancedTranslationQueue:
    """增强版翻译任务队列，支持多线程并发处理"""

    def __init__(self):
        """初始化翻译队列，但不创建处理器，等待配置"""
        # 默认配置 - 限制最大并发翻译任务为10个
        self.max_concurrent_tasks = 10
        self.task_timeout = 3600  # 1小时
        self.retry_times = 3

        # 任务存储
        self.tasks: Dict[str, TranslationTask] = {}
        self.user_tasks: Dict[int, str] = {}
        self.active_tasks: Dict[str, TranslationTask] = {}

        # 状态控制
        self.initialized = False
        self.running = False
        self.lock = threading.RLock()
        self.task_available = threading.Event()
        
        # 线程池健康状态
        self.last_pool_check = time.time()
        self.pool_check_interval = 300  # 5分钟检查一次线程池健康状态
        self.db_recycle_interval = 1800  # 30分钟回收一次数据库连接

        # 日志记录器
        self.logger = logging.getLogger(f"{__name__}.queue")

    def configure(self, max_concurrent_tasks: Optional[int] = None,
                task_timeout: Optional[int] = None,
                retry_times: Optional[int] = None) -> None:
        """
        配置任务队列参数

        Args:
            max_concurrent_tasks: 最大并发任务数
            task_timeout: 任务超时时间（秒）
            retry_times: 任务重试次数
        """
        with self.lock:
            # 更新配置
            if max_concurrent_tasks is not None:
                self.max_concurrent_tasks = max_concurrent_tasks
            if task_timeout is not None:
                self.task_timeout = task_timeout
            if retry_times is not None:
                self.retry_times = retry_times

            # 如果已经初始化，需要重新启动处理器
            if self.initialized:
                self.stop_processor()
                self.start_processor()
            else:
                self.start_processor()
                self.initialized = True
                
                # 启动定期回收数据库连接的后台线程
                self.schedule_db_connection_recycling()

    def add_task(self, user_id: int, user_name: str, file_path: str,
                task_type: str = 'ppt_translate', source_language: str = 'en',
                target_language: str = 'zh-cn', priority: int = 0,
                annotation_filename: str = None, annotation_json: Dict = None,
                select_page: List[int] = None, bilingual_translation: bool = False, **kwargs) -> int:
        """
        添加任务到队列

        Args:
            user_id: 用户ID
            user_name: 用户名
            file_path: 文件路径
            task_type: 任务类型 (ppt_translate, pdf_annotate)
            source_language: 源语言
            target_language: 目标语言
            priority: 优先级
            annotation_filename: 注释文件名
            annotation_json: 注释数据（直接传递）
            select_page: 选择的页面列表
            bilingual_translation: 是否双语翻译
            **kwargs: 其他参数

        Returns:
            队列位置
        """
        if not self.initialized:
            raise RuntimeError("任务队列未初始化")

        with self.lock:
            # 检查当前活跃任务数量，确保不超过限制
            active_count = len(self.active_tasks)
            waiting_count = len([t for t in self.tasks.values() if t.status == "waiting"])
            total_count = active_count + waiting_count

            if total_count >= self.max_concurrent_tasks:
                self.logger.warning(
                    f"任务队列已满 - 活跃任务: {active_count}, 等待任务: {waiting_count}, "
                    f"最大限制: {self.max_concurrent_tasks}"
                )
                raise RuntimeError(f"任务队列已满，当前有 {total_count} 个任务，最大限制为 {self.max_concurrent_tasks} 个")

            # 生成任务ID
            task_id = f"task_{int(time.time())}_{user_id}"

            # 创建任务对象
            task = TranslationTask(
                task_id=task_id,
                user_id=user_id,
                user_name=user_name,
                file_path=file_path,
                task_type=task_type,
                source_language=source_language,
                target_language=target_language,
                priority=priority,
                annotation_filename=annotation_filename,
                annotation_json=annotation_json,  # 添加注释数据
                select_page=select_page,
                bilingual_translation=bilingual_translation,
                **kwargs
            )

            # 存储任务
            self.tasks[task_id] = task
            self.user_tasks[user_id] = task_id

            # 通知处理器有新任务
            self.task_available.set()

            self.logger.info(
                f"新任务已添加 - ID: {task_id}, 用户: {user_name}, "
                f"文件: {os.path.basename(file_path)}"
            )

            # 返回队列中等待的任务数
            return len([t for t in self.tasks.values() if t.status == "waiting"])

    def start_processor(self) -> None:
        """启动任务处理器"""
        with self.lock:
            if not self.running:
                self.logger.info("正在启动任务处理器...")
                self.running = True

                # 检查线程池健康状态
                self._check_thread_pool_health()

                # 创建处理器线程
                self.processor_thread = threading.Thread(
                    target=self._processor_loop,
                    name="translation_processor",
                    daemon=False
                )
                self.processor_thread.start()

                self.logger.info(
                    f"任务处理器已启动 - 最大并发任务数: {self.max_concurrent_tasks}, "
                    f"超时时间: {self.task_timeout}秒"
                )

    def stop_processor(self) -> None:
        """停止任务处理器"""
        with self.lock:
            if self.running:
                self.logger.info("正在停止任务处理器...")
                self.running = False
                self.task_available.set()  # 唤醒处理器线程

                if hasattr(self, 'processor_thread'):
                    self.processor_thread.join()

                self.logger.info("任务处理器已停止")

    def _processor_loop(self) -> None:
        """任务处理器主循环"""
        while self.running:
            try:
                # 等待新任务或检查间隔
                self.task_available.wait(timeout=1.0)
                self.task_available.clear()
                
                # 定期检查线程池健康状态
                current_time = time.time()
                if current_time - self.last_pool_check > self.pool_check_interval:
                    self._check_thread_pool_health()
                    self.last_pool_check = current_time

                with self.lock:
                    # 检查是否可以启动新任务
                    if len(self.active_tasks) >= self.max_concurrent_tasks:
                        continue

                    # 获取等待中的任务
                    waiting_tasks = [
                        t for t in self.tasks.values()
                        if t.status == "waiting"
                    ]

                    if not waiting_tasks:
                        continue

                    # 按优先级排序
                    waiting_tasks.sort(key=lambda x: x.priority)

                    # 选择要处理的任务
                    for task in waiting_tasks:
                        if len(self.active_tasks) >= self.max_concurrent_tasks:
                            break

                        if task.task_id not in self.active_tasks:
                            # 提交任务到线程池
                            self._process_task(task)

            except Exception as e:
                self.logger.error(f"任务处理器错误: {str(e)}")
                time.sleep(1)  # 发生错误时短暂暂停
                
                # 如果发生异常，检查线程池健康状态
                self._check_thread_pool_health()

    def _check_thread_pool_health(self) -> bool:
        """
        检查线程池健康状态，如果异常则尝试重新初始化
        
        Returns:
            线程池是否健康
        """
        try:
            if not thread_pool.initialized:
                self.logger.warning("线程池未初始化，尝试重新初始化")
                thread_pool.configure()
                return False
                
            # 获取线程池统计信息
            stats = thread_pool.get_stats()
            io_count = thread_pool.get_io_active_count()
            cpu_count = thread_pool.get_cpu_active_count()
            
            self.logger.info(f"线程池健康检查 - IO线程: {io_count}, CPU线程: {cpu_count}, " 
                            f"总任务: {stats.get('total_tasks_created', 0)}")
            
            # 检查线程池是否正常工作
            if io_count == 0 and stats.get('total_tasks_created', 0) > 0:
                self.logger.warning("线程池IO线程数为0，可能异常，尝试重新初始化")
                thread_pool.configure()
                return False
                
            return True
        except Exception as e:
            self.logger.error(f"检查线程池健康状态时出错: {str(e)}")
            # 出错时尝试重新初始化线程池
            try:
                thread_pool.configure()
            except Exception as e2:
                self.logger.error(f"重新初始化线程池失败: {str(e2)}")
            return False

    def _process_task(self, task: TranslationTask) -> None:
        """
        处理任务，将任务提交到线程池执行
        
        Args:
            task: 要处理的任务
        """
        try:
            # 如果任务已经取消或失败，直接返回
            if task.status in ["canceled", "failed"]:
                return
            
            # 更新任务状态
            task.status = "processing"
            task.started_at = datetime.now()
            
            # 添加到活跃任务列表
            with self.lock:
                self.active_tasks[task.task_id] = task
            
            # 检查线程池健康状态
            self._check_thread_pool_health()
            
            # 记录任务日志
            self.logger.info(f"提交任务到线程池: {task.task_id}, 用户: {task.user_id}")
            task.logger.info(f"准备处理翻译任务: {os.path.basename(task.file_path)}")
            
            # 定义任务完成回调函数
            def task_done_callback(thread_task):
                try:
                    # 检查任务状态
                    if thread_task.status == TaskStatus.COMPLETED:
                        task.status = "completed"
                        task.completed_at = datetime.now()
                        task.event.set()
                        self.logger.info(f"任务完成: {task.task_id}")
                    elif thread_task.status == TaskStatus.FAILED:
                        task.status = "failed"
                        task.error = str(thread_task.error)
                        task.completed_at = datetime.now()
                        task.event.set()
                        self.logger.error(f"任务失败: {task.task_id}, 错误: {task.error}")
                    elif thread_task.status == TaskStatus.CANCELED:
                        task.status = "canceled"
                        task.completed_at = datetime.now()
                        task.event.set()
                        self.logger.info(f"任务已取消: {task.task_id}")
                    
                    # 清理任务资源
                    self._cleanup_task_resources(task)
                    
                    # 从活跃任务列表中移除
                    with self.lock:
                        if task.task_id in self.active_tasks:
                            del self.active_tasks[task.task_id]
                    
                    # 通知任务队列有新的处理空间
                    self.task_available.set()
                    
                except Exception as e:
                    self.logger.error(f"任务完成回调出错: {task.task_id}, 错误: {str(e)}")
                    
                    # 确保任务被从活跃列表中移除
                    with self.lock:
                        if task.task_id in self.active_tasks:
                            del self.active_tasks[task.task_id]
                    
                    # 通知任务队列有新的处理空间
                    self.task_available.set()
            
            # 提交任务到线程池
            thread_task = thread_pool.submit(
                func=self._execute_task,
                args=(task,),
                kwargs={},
                task_type=TaskType.IO_BOUND,
                priority=task.priority,
                task_id=task.task_id,
                timeout=self.task_timeout
            )
            
            # 添加任务完成回调
            thread_task.add_callback(task_done_callback)
            
            # 保存线程任务引用
            task.thread_task = thread_task
            
        except Exception as e:
            error_msg = f"提交任务到线程池失败: {str(e)}"
            self.logger.exception(error_msg)
            task.logger.error(error_msg)
            
            # 更新任务状态为失败
            task.error = f"{str(e)}\n{traceback.format_exc()}"
            task.status = "failed"
            task.completed_at = datetime.now()
            task.event.set()
            
            # 从活跃任务列表中移除
            with self.lock:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
            
            # 通知任务队列有新的处理空间
            self.task_available.set()
            
            # 处理任务错误
            self._handle_task_error(task, error_msg)

    def _execute_task(self, task: TranslationTask) -> bool:
        """
        执行翻译任务
        
        Args:
            task: 要执行的任务
            
        Returns:
            任务是否成功执行
        """
        try:
            # 设置任务开始时间
            task_start_time = time.time()
            self.logger.info(f"开始执行任务: {task.task_id}, 类型: {task.task_type}")
            
            # 记录任务日志
            current_time = datetime.now()
            task.logs.append({
                'timestamp': current_time,
                'message': f"开始执行任务: {os.path.basename(task.file_path)}",
                'level': 'info'
            })
            
            # 记录数据库连接使用情况
            from flask import current_app
            engine = current_app.extensions['sqlalchemy'].db.engine
            db_conn_before = {
                'checkedin': engine.pool.checkedin(),
                'checkedout': engine.pool.checkedout(),
                'overflow': engine.pool.overflow()
            }
            
            # 根据任务类型执行不同的操作
            success = False
            
            # 进度回调函数
            def progress_callback(current, total):
                # 检查任务是否被取消
                if task.status == "canceled" or (task.thread_task and task.thread_task.should_cancel()):
                    raise RuntimeError("任务已被用户取消")
                    
                progress = int((current / total) * 100) if total > 0 else 0
                task.progress = progress
                task.current_slide = current
                task.total_slides = total
                
                # 记录任务进度
                if progress % 10 == 0 or progress == 100:  # 每10%记录一次
                    log_message = f"处理进度: {current}/{total} ({progress}%)"
                    task.logger.info(log_message)
                    
                    # 添加到任务日志
                    task.logs.append({
                        'timestamp': datetime.now(),
                        'message': log_message,
                        'level': 'info'
                    })
                    
                # 检查任务执行时间，对于长时间运行的任务进行资源优化
                elapsed_time = time.time() - task_start_time
                if elapsed_time > 600:  # 10分钟
                    # 检查数据库连接情况，如果有大量溢出连接，尝试回收
                    current_overflow = engine.pool.overflow()
                    if current_overflow > 5:  # 有多个溢出连接
                        try:
                            # 尝试回收空闲连接
                            self.logger.warning(f"长时间运行任务 {task.task_id} 检测到 {current_overflow} 个溢出连接，尝试回收")
                            with engine.connect() as conn:
                                conn.execute(text("/* 长任务内部回收连接检查 */ SELECT 1"))
                        except Exception as e:
                            self.logger.error(f"长时间任务中回收连接失败: {str(e)}")
                
                # 保留最近的50条日志
                if len(task.logs) > 50:
                    task.logs = task.logs[-50:]
            
            # 执行具体的任务逻辑
            if task.task_type == 'ppt_translate':
                success = self._execute_ppt_translation_task(task, progress_callback)
            elif task.task_type == 'pdf_annotate':
                success = self._execute_pdf_annotation_task(task, progress_callback)
            else:
                raise ValueError(f"不支持的任务类型: {task.task_type}")
            
            # 记录数据库连接使用情况变化
            db_conn_after = {
                'checkedin': engine.pool.checkedin(),
                'checkedout': engine.pool.checkedout(),
                'overflow': engine.pool.overflow()
            }
            
            # 检查是否有连接泄漏
            if db_conn_after['checkedout'] > db_conn_before['checkedout']:
                self.logger.warning(
                    f"任务 {task.task_id} 完成后检测到可能的连接泄漏: "
                    f"签出连接数从 {db_conn_before['checkedout']} 增加到 {db_conn_after['checkedout']}"
                )
                
                # 尝试主动回收连接
                try:
                    self.logger.info(f"尝试回收连接池中的空闲连接")
                    engine.dispose()
                except Exception as e:
                    self.logger.error(f"回收连接失败: {str(e)}")
            
            # 任务完成时间
            task_end_time = time.time()
            elapsed_time = task_end_time - task_start_time
            
            # 记录任务完成日志
            log_level = 'info' if success else 'error'
            log_message = f"任务{'成功完成' if success else '执行失败'}，耗时: {elapsed_time:.2f}秒"
            
            # 记录完成日志
            task.logger.log(logging.INFO if success else logging.ERROR, log_message)
            task.logs.append({
                'timestamp': datetime.now(),
                'message': log_message,
                'level': log_level
            })
            
            # 对于特别长时间运行的任务，进行垃圾回收
            if elapsed_time > 1800:  # 30分钟
                self.logger.warning(f"长时间运行任务 {task.task_id} 已完成，耗时 {elapsed_time:.2f}秒，执行资源回收")
                # 尝试手动垃圾回收
                import gc
                gc.collect()
            
            # 返回任务结果
            return success
            
        except Exception as e:
            # 记录错误信息
            error_msg = f"任务执行异常: {str(e)}"
            task.error = f"{str(e)}\n{traceback.format_exc()}"
            task.logger.error(error_msg)
            
            # 记录错误日志
            task.logs.append({
                'timestamp': datetime.now(),
                'message': error_msg,
                'level': 'error'
            })
            
            # 保留最近的50条日志
            if len(task.logs) > 50:
                task.logs = task.logs[-50:]
                
            return False

    def _execute_ppt_translation_task(self, task: TranslationTask, progress_callback) -> bool:
        """
        执行PPT翻译任务

        Args:
            task: 翻译任务对象
            progress_callback: 进度回调函数

        Returns:
            bool: 处理是否成功
        """
        try:
            # 导入翻译函数
            from ..function.ppt_translate_async import process_presentation, process_presentation_add_annotations

            # 停止词列表和自定义翻译字典（这里可以从数据库获取或使用默认值）
            stop_words_list = []
            custom_translations = {}

            # 判断是否有注释数据
            if task.annotation_json:
                self.logger.info(f"处理带注释的PPT翻译任务: {task.annotation_filename}")

                # 使用带注释的处理函数
                result = process_presentation_add_annotations(
                    presentation_path=task.file_path,
                    annotations=task.annotation_json,  # 直接使用注释数据
                    stop_words=stop_words_list,
                    custom_translations=custom_translations,
                    source_language=task.source_language,
                    target_language=task.target_language,
                    bilingual_translation=str(int(task.bilingual_translation)),
                    progress_callback=progress_callback
                )
            else:
                # 使用普通处理函数
                result = process_presentation(
                    presentation_path=task.file_path,
                    stop_words=stop_words_list,
                    custom_translations=custom_translations,
                    select_page=task.select_page,
                    source_language=task.source_language,
                    target_language=task.target_language,
                    bilingual_translation=str(int(task.bilingual_translation)),
                    progress_callback=progress_callback
                )

            return result

        except Exception as e:
            self.logger.error(f"执行PPT翻译任务时出错: {str(e)}")
            return False

    def _execute_pdf_annotation_task(self, task: TranslationTask, progress_callback) -> bool:
        """
        执行PDF注释任务

        Args:
            task: 翻译任务对象
            progress_callback: 进度回调函数

        Returns:
            bool: 处理是否成功
        """
        try:
            # 导入PDF注释处理函数
            from ..function.pdf_annotate_async import process_pdf_annotations_async
            import asyncio

            # 设置输出路径
            if not task.output_path:
                # 如果没有指定输出路径，生成默认路径
                base_name = os.path.splitext(task.file_path)[0]
                task.output_path = f"{base_name}_annotated.pdf"

            # 创建异步事件循环并执行PDF注释处理
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(
                    process_pdf_annotations_async(
                        pdf_path=task.file_path,
                        annotations=task.annotations,
                        output_path=task.output_path,
                        progress_callback=progress_callback
                    )
                )
                return result
            finally:
                loop.close()

        except Exception as e:
            self.logger.error(f"执行PDF注释任务时出错: {str(e)}")
            return False

    def _schedule_database_update(self, task: TranslationTask) -> None:
        """
        调度数据库更新任务

        Args:
            task: 翻译任务对象
        """
        # 简单的方法：记录任务完成状态，让其他地方处理数据库更新
        self.logger.info(f"任务完成 - ID: {task.task_id}, 用户: {task.user_name}, 文件: {os.path.basename(task.file_path)}")

        # 可以在这里添加其他通知机制，比如：
        # 1. 发送消息到消息队列
        # 2. 写入文件
        # 3. 发送HTTP请求到主应用

        # 暂时跳过数据库更新以避免线程冲突
        # 数据库状态可以通过其他方式同步，比如定期检查任务状态

    def _handle_task_error(self, task: TranslationTask, error: str) -> None:
        """
        处理任务错误
        
        Args:
            task: 出错的任务
            error: 错误信息
        """
        self.logger.error(f"任务错误: {task.task_id}, 错误: {error}")
        task.logger.error(f"翻译任务失败: {error}")
        
        # 更新任务错误信息
        task.error = error
        
        # 检查是否可以重试
        if task.retry_count < self.retry_times:
            task.retry_count += 1
            task.status = "waiting"
            task.progress = 0
            task.logger.info(f"准备重试任务 (第{task.retry_count}次)")
            
            # 更新当前操作信息
            current_time = datetime.now()
            task.logs.append({
                'timestamp': current_time,
                'message': f"任务失败，准备重试 ({task.retry_count}/{self.retry_times}): {error}",
                'level': 'warning'
            })
            
            # 保留最近的50条日志
            if len(task.logs) > 50:
                task.logs = task.logs[-50:]
            
            # 从活跃任务列表中移除
            with self.lock:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
            
            # 通知任务队列有新的处理空间
            self.task_available.set()
            
        else:
            # 超过重试次数，标记为失败
            task.status = "failed"
            task.completed_at = datetime.now()
            task.event.set()  # 设置事件，通知等待的线程
            
            # 任务最终失败后清理资源
            self._cleanup_task_resources(task)
            
            # 更新当前操作信息
            current_time = datetime.now()
            task.logs.append({
                'timestamp': current_time,
                'message': f"任务最终失败 (已重试{task.retry_count}次): {error}",
                'level': 'error'
            })
            
            # 保留最近的50条日志
            if len(task.logs) > 50:
                task.logs = task.logs[-50:]
            
            # 从活跃任务列表中移除
            with self.lock:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
            
            # 通知任务队列有新的处理空间
            self.task_available.set()
            
            # 更新数据库中的任务状态
            self._schedule_database_update(task)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息字典
        """
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None

            return {
                'task_id': task.task_id,
                'status': task.status,
                'progress': task.progress,
                'current_slide': getattr(task, 'current_slide', 0),
                'total_slides': getattr(task, 'total_slides', 0),
                'error': task.error,
                'start_time': task.start_time,
                'end_time': task.end_time,
                'retry_count': task.retry_count
            }

    def get_task_status_by_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        按用户ID获取任务状态

        Args:
            user_id: 用户ID

        Returns:
            任务状态信息字典
        """
        with self.lock:
            # 从用户任务映射中获取任务ID
            task_id = self.user_tasks.get(user_id)
            if not task_id:
                return None

            # 获取任务对象
            task = self.tasks.get(task_id)
            if not task:
                return None

            # 计算队列位置（仅对等待中的任务）
            position = 0
            if task.status == "waiting":
                waiting_tasks = [t for t in self.tasks.values() if t.status == "waiting"]
                waiting_tasks.sort(key=lambda x: x.created_at)
                for i, waiting_task in enumerate(waiting_tasks):
                    if waiting_task.task_id == task_id:
                        position = i + 1
                        break

            return {
                'task_id': task.task_id,
                'status': task.status,
                'progress': task.progress,
                'current_slide': getattr(task, 'current_slide', 0),
                'total_slides': getattr(task, 'total_slides', 0),
                'position': position,
                'error': task.error,
                'start_time': task.start_time,
                'end_time': task.end_time,
                'retry_count': task.retry_count,
                'created_at': task.created_at,
                'started_at': getattr(task, 'started_at', None),
                'completed_at': getattr(task, 'completed_at', None)
            }

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        获取队列统计信息

        Returns:
            统计信息字典
        """
        with self.lock:
            waiting_tasks = len([t for t in self.tasks.values() if t.status == "waiting"])
            processing_tasks = len(self.active_tasks)
            completed_tasks = len([t for t in self.tasks.values() if t.status == "completed"])
            failed_tasks = len([t for t in self.tasks.values() if t.status == "failed"])
            canceled_tasks = len([t for t in self.tasks.values() if t.status == "canceled"])

            return {
                'waiting': waiting_tasks,
                'processing': processing_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks,
                'canceled': canceled_tasks,
                'total': len(self.tasks),
                'max_concurrent': self.max_concurrent_tasks,
                'task_timeout': self.task_timeout,
                'retry_times': self.retry_times
            }

    def get_queue_size(self) -> int:
        """
        获取队列总大小
        
        Returns:
            队列中的任务总数
        """
        with self.lock:
            return len(self.tasks)
    
    def get_active_count(self) -> int:
        """
        获取活动任务数
        
        Returns:
            当前正在处理的任务数
        """
        with self.lock:
            return len(self.active_tasks)
    
    def get_waiting_count(self) -> int:
        """
        获取等待任务数
        
        Returns:
            等待处理的任务数
        """
        with self.lock:
            return len([t for t in self.tasks.values() if t.status == "waiting"])
    
    def get_completed_count(self) -> int:
        """
        获取已完成任务数
        
        Returns:
            已完成的任务数
        """
        with self.lock:
            return len([t for t in self.tasks.values() if t.status == "completed"])
    
    def get_failed_count(self) -> int:
        """
        获取失败任务数
        
        Returns:
            失败的任务数
        """
        with self.lock:
            return len([t for t in self.tasks.values() if t.status == "failed"])

    def recycle_idle_connections(self) -> Dict[str, Any]:
        """
        回收闲置的数据库连接
        
        该方法会关闭所有空闲的数据库连接并强制回收连接池中的资源
        对于长时间运行的应用程序，定期调用此方法可以防止连接泄漏
        
        Returns:
            回收结果的状态信息
        """
        from flask import current_app
        from sqlalchemy import create_engine, text
        import time
        
        try:
            # 获取当前数据库引擎
            engine = current_app.extensions['sqlalchemy'].db.engine
            
            # 记录回收前的连接池状态
            before_status = {
                'pool_size': engine.pool.size(),
                'checkedin': engine.pool.checkedin(),
                'checkedout': engine.pool.checkedout(),
                'overflow': engine.pool.overflow()
            }
            
            # 创建一个临时连接执行回收命令
            start_time = time.time()
            with engine.connect() as conn:
                # 执行连接池回收
                conn.execute(text("/* 回收空闲连接 */ SELECT 1"))
                
            # 强制回收所有空闲连接
            engine.dispose()
            
            # 记录回收后的连接池状态
            after_status = {
                'pool_size': engine.pool.size(),
                'checkedin': engine.pool.checkedin(),
                'checkedout': engine.pool.checkedout(),
                'overflow': engine.pool.overflow()
            }
            
            execution_time = time.time() - start_time
            
            return {
                'success': True,
                'message': '成功回收空闲连接',
                'before': before_status,
                'after': after_status,
                'execution_time': execution_time
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'回收连接失败: {str(e)}',
                'error': str(e)
            }
    
    def _cleanup_task_resources(self, task: TranslationTask) -> None:
        """
        清理任务资源
        
        当任务完成或失败时，清理相关资源，确保内存和数据库连接被正确释放
        
        Args:
            task: 要清理资源的任务
        """
        try:
            # 记录开始清理
            self.logger.info(f"清理任务资源: {task.task_id}, 用户: {task.user_id}")
            
            # 确保数据库会话被关闭
            from flask import current_app
            db = current_app.extensions['sqlalchemy'].db
            
            # 如果任务有自己的会话，关闭它
            if hasattr(task, 'db_session') and task.db_session:
                try:
                    task.db_session.close()
                    self.logger.info(f"已关闭任务专用数据库会话: {task.task_id}")
                except Exception as e:
                    self.logger.warning(f"关闭任务数据库会话失败: {str(e)}")
            
            # 强制垃圾回收大型对象
            if hasattr(task, 'result') and task.result:
                task.result = None
            
            # 清理任务中可能持有的大型数据
            for attr in ['annotations', 'annotation_json']:
                if hasattr(task, attr) and getattr(task, attr):
                    setattr(task, attr, None)
            
            # 如果任务持续时间超过30分钟，建议回收一下连接池
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                if duration > 1800:  # 30分钟
                    self.logger.info(f"长时间运行任务({duration:.1f}秒)完成，建议回收连接池")
                    
            self.logger.info(f"任务资源清理完成: {task.task_id}")
            
        except Exception as e:
            self.logger.error(f"清理任务资源时出错: {str(e)}")

    def schedule_db_connection_recycling(self, interval=None):
        """
        启动定期回收数据库连接的后台线程
        
        Args:
            interval: 回收间隔（秒），默认使用self.db_recycle_interval
        """
        if interval is not None:
            self.db_recycle_interval = interval
            
        def _recycle_job():
            self.logger.info(f"启动数据库连接定期回收线程，间隔：{self.db_recycle_interval}秒")
            while self.running:
                try:
                    # 等待指定间隔
                    time.sleep(self.db_recycle_interval)
                    
                    # 如果任务队列不再运行，退出循环
                    if not self.running:
                        break
                    
                    # 执行回收
                    self.logger.info("执行定期数据库连接回收")
                    result = self.recycle_idle_connections()
                    
                    if result and result.get('success'):
                        self.logger.info(f"定期回收数据库连接成功：回收前 {result['before']}，回收后 {result['after']}")
                    else:
                        self.logger.warning(f"定期回收数据库连接失败：{result.get('message', '未知错误')}")
                        
                except Exception as e:
                    self.logger.error(f"定期回收数据库连接异常: {str(e)}")
                    # 出错后短暂暂停，避免频繁失败
                    time.sleep(60)
                    
        # 启动后台线程
        recycle_thread = threading.Thread(
            target=_recycle_job,
            name="db_connection_recycler",
            daemon=True  # 使用守护线程，主线程结束时自动结束
        )
        recycle_thread.start()
        
        self.logger.info("数据库连接定期回收线程已启动")

# 创建全局翻译队列实例
translation_queue = EnhancedTranslationQueue()