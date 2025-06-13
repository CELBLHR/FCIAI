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

    def _process_task(self, task: TranslationTask) -> None:
        """
        处理单个翻译任务

        Args:
            task: 翻译任务对象
        """
        try:
            # 更新任务状态
            task.status = "processing"
            task.start_time = datetime.now()
            self.active_tasks[task.task_id] = task

            # 提交到线程池
            thread_pool.submit(
                func=self._execute_task,
                args=(task,),
                task_type=TaskType.IO_BOUND,
                priority=task.priority,
                task_id=task.task_id,
                timeout=self.task_timeout
            )

            self.logger.info(
                f"开始处理任务 - ID: {task.task_id}, "
                f"用户: {task.user_name}"
            )

        except Exception as e:
            self.logger.error(f"提交任务失败 - ID: {task.task_id}, 错误: {str(e)}")
            self._handle_task_error(task, str(e))

    def _execute_task(self, task: TranslationTask) -> None:
        """
        执行任务

        Args:
            task: 任务对象
        """
        try:
            # 进度回调函数，用于更新任务进度
            def progress_callback(current, total):
                if total > 0:
                    progress = int((current / total) * 100)
                    task.progress = progress
                    task.current_slide = current
                    task.total_slides = total

            # 根据任务类型执行不同的处理
            if task.task_type == 'pdf_annotate':
                result = self._execute_pdf_annotation_task(task, progress_callback)
            else:  # 默认为PPT翻译
                result = self._execute_ppt_translation_task(task, progress_callback)

            # 更新任务状态
            if result:
                task.status = "completed"
                task.progress = 100

                # 更新数据库记录 - 使用延迟更新避免线程冲突
                try:
                    # 将数据库更新任务添加到队列中，由主线程处理
                    self._schedule_database_update(task)
                except Exception as e:
                    self.logger.error(f"调度数据库更新时出错: {str(e)}")
            else:
                raise Exception(f"{task.task_type} 处理失败")

        except Exception as e:
            self.logger.error(f"执行任务时出错 - ID: {task.task_id}, 错误: {str(e)}")
            self._handle_task_error(task, str(e))

        finally:
            # 清理活动任务
            with self.lock:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]

            # 通知处理器可以处理新任务
            self.task_available.set()

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
            task: 翻译任务对象
            error: 错误信息
        """
        with self.lock:
            task.error = error
            task.retry_count += 1

            if task.retry_count < self.retry_times:
                # 重试任务
                task.status = "waiting"
                self.logger.warning(
                    f"任务将重试 - ID: {task.task_id}, "
                    f"重试次数: {task.retry_count}/{self.retry_times}"
                )
            else:
                # 标记任务失败
                task.status = "failed"
                task.end_time = datetime.now()
                self.logger.error(
                    f"任务失败 - ID: {task.task_id}, "
                    f"重试次数已达上限: {self.retry_times}"
                )

            # 从活动任务中移除
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]

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

# 创建全局翻译队列实例
translation_queue = EnhancedTranslationQueue()