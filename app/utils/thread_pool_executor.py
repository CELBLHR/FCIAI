"""
增强型线程池执行器
支持优先级任务、任务状态跟踪和异步I/O操作
"""
import threading
import queue
import time
import os
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto
from typing import Dict, Any, Callable, List, Optional, Union, TypeVar, Generic
import logging
import asyncio
from functools import partial
import traceback

# 任务类型定义
class TaskType(Enum):
    """任务类型枚举"""
    HIGH_PRIORITY = auto()
    IO_BOUND = auto()
    CPU_BOUND = auto()
    LOW_PRIORITY = auto()

# 任务状态定义
class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = 'pending'    # 等待执行
    RUNNING = 'running'    # 正在执行
    COMPLETED = 'completed'  # 已完成
    FAILED = 'failed'      # 执行失败
    CANCELED = 'canceled'  # 已取消

# 任务结果泛型类型
T = TypeVar('T')

class Task(Generic[T]):
    """任务对象，包含任务信息和执行状态"""
    
    def __init__(self, 
                func: Callable, 
                args: tuple = (), 
                kwargs: Dict[str, Any] = None,
                task_type: TaskType = TaskType.IO_BOUND,
                task_id: str = None,
                timeout: float = None,
                priority: int = 0):
        """
        初始化任务
        
        Args:
            func: 要执行的函数
            args: 位置参数
            kwargs: 关键字参数
            task_type: 任务类型，用于任务调度
            task_id: 任务唯一标识符
            timeout: 任务超时时间（秒）
            priority: 任务优先级（数字越小优先级越高）
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.task_type = task_type
        self.task_id = task_id or f"task_{threading.get_ident()}_{int(time.time() * 1000)}"
        self.timeout = timeout
        self.priority = priority
        
        # 任务状态信息
        self.status = TaskStatus.PENDING
        self.result: Optional[T] = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.progress = 0
        
        # 回调函数
        self.callbacks = []
        
        # 用于任务取消的事件
        self.cancel_event = threading.Event()
    
    def should_cancel(self) -> bool:
        """检查任务是否应该取消"""
        return self.cancel_event.is_set()
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """添加任务完成后的回调函数"""
        self.callbacks.append(callback)
    
    def cancel(self) -> bool:
        """尝试取消任务，如果任务已经开始执行则返回False"""
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.CANCELED
            self.cancel_event.set()
            return True
        elif self.status == TaskStatus.RUNNING:
            # 仅设置取消标志，由执行函数决定是否中断
            self.cancel_event.set()
            return True
        return False
    
    def get_info(self) -> Dict[str, Any]:
        """获取任务信息"""
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'progress': self.progress,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'error': str(self.error) if self.error else None,
            'task_type': self.task_type.name,
            'priority': self.priority
        }

class EnhancedThreadPoolExecutor:
    """增强型线程池执行器，支持优先级队列和异步操作"""
    
    def __init__(self):
        """初始化线程池，但不创建执行器，等待配置"""
        # 默认配置
        self.max_workers = min(32, os.cpu_count() * 2)
        self.io_bound_workers = int(self.max_workers * 0.75)
        self.cpu_bound_workers = os.cpu_count()
        self.thread_name_prefix = "worker"
        
        # 状态变量
        self.initialized = False
        self.running = False
        self.lock = threading.RLock()
        
        # 任务相关
        self.tasks: Dict[str, Task] = {}
        self.task_count = 0
        self.task_queues = {
            TaskType.HIGH_PRIORITY: queue.PriorityQueue(),
            TaskType.IO_BOUND: queue.PriorityQueue(),
            TaskType.CPU_BOUND: queue.PriorityQueue(),
            TaskType.LOW_PRIORITY: queue.PriorityQueue(),
        }
        
        # 日志记录器
        self.logger = logging.getLogger(__name__)
    
    def configure(self, max_workers: Optional[int] = None, 
                io_bound_workers: Optional[int] = None,
                cpu_bound_workers: Optional[int] = None,
                thread_name_prefix: Optional[str] = None) -> None:
        """
        配置线程池参数
        
        Args:
            max_workers: 最大工作线程数
            io_bound_workers: I/O密集型任务的工作线程数
            cpu_bound_workers: CPU密集型任务的工作线程数
            thread_name_prefix: 线程名称前缀
        """
        with self.lock:
            # 更新配置
            if max_workers is not None:
                self.max_workers = max_workers
            if io_bound_workers is not None:
                self.io_bound_workers = io_bound_workers
            if cpu_bound_workers is not None:
                self.cpu_bound_workers = cpu_bound_workers
            if thread_name_prefix is not None:
                self.thread_name_prefix = thread_name_prefix
            
            # 如果已经初始化，需要重新创建执行器
            if self.initialized:
                self._shutdown_executors()
                self._create_executors()
            else:
                self._create_executors()
                self.initialized = True
    
    def _create_executors(self) -> None:
        """创建线程池执行器"""
        self.io_executor = ThreadPoolExecutor(
            max_workers=self.io_bound_workers,
            thread_name_prefix=f"{self.thread_name_prefix}_io"
        )
        
        self.cpu_executor = ThreadPoolExecutor(
            max_workers=self.cpu_bound_workers,
            thread_name_prefix=f"{self.thread_name_prefix}_cpu"
        )
        
        self.running = True
        
        # 启动调度线程
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name=f"{self.thread_name_prefix}_scheduler",
            daemon=True
        )
        self.scheduler_thread.start()
        
        self.logger.info(
            f"线程池已创建 - IO线程: {self.io_bound_workers}, "
            f"CPU线程: {self.cpu_bound_workers}"
        )
    
    def _shutdown_executors(self) -> None:
        """关闭线程池执行器"""
        self.running = False
        
        if hasattr(self, 'io_executor'):
            self.io_executor.shutdown(wait=True)
        if hasattr(self, 'cpu_executor'):
            self.cpu_executor.shutdown(wait=True)
        
        # 等待调度线程结束
        if hasattr(self, 'scheduler_thread') and self.scheduler_thread.is_alive():
            self.scheduler_thread.join()
        
        self.logger.info("线程池已关闭")
    
    def submit(self, func: Callable, args: tuple = (), 
              kwargs: Dict[str, Any] = None,
              task_type: TaskType = TaskType.IO_BOUND,
              priority: int = 0,
              task_id: str = None,
              timeout: float = None) -> Task:
        """
        提交任务到线程池
        
        Args:
            func: 要执行的函数
            args: 位置参数
            kwargs: 关键字参数
            task_type: 任务类型
            priority: 任务优先级（数字越小优先级越高）
            task_id: 任务ID
            timeout: 任务超时时间（秒）
            
        Returns:
            任务对象
        """
        if not self.initialized:
            raise RuntimeError("线程池未初始化")
        
        with self.lock:
            # 生成任务ID
            if task_id is None:
                self.task_count += 1
                task_id = f"task_{self.task_count}"
            
            # 创建任务对象
            task = Task(
                task_id=task_id,
                func=func,
                args=args,
                kwargs=kwargs or {},
                task_type=task_type,
                priority=priority,
                timeout=timeout
            )
            
            # 存储任务
            self.tasks[task_id] = task
            
            # 将任务加入对应的优先级队列
            self.task_queues[task_type].put((priority, task))
            
            self.logger.debug(
                f"任务已提交 - ID: {task_id}, 类型: {task_type.name}, "
                f"优先级: {priority}"
            )
            
            return task
    
    def _scheduler_loop(self) -> None:
        """任务调度循环"""
        while self.running:
            try:
                # 按优先级顺序检查队列
                for task_type in TaskType:
                    if not self.task_queues[task_type].empty():
                        # 获取任务
                        _, task = self.task_queues[task_type].get_nowait()
                        
                        # 选择执行器
                        executor = (self.io_executor 
                                  if task.task_type in (TaskType.IO_BOUND, TaskType.HIGH_PRIORITY)
                                  else self.cpu_executor)
                        
                        # 提交任务到执行器
                        future = executor.submit(
                            self._execute_task,
                            task
                        )
                        
                        # 添加回调
                        future.add_done_callback(
                            lambda f, t=task: self._task_done_callback(f, t)
                        )
                        
                        break
                
                # 短暂休眠以避免CPU过度使用
                threading.Event().wait(0.01)
                
            except Exception as e:
                self.logger.error(f"调度器错误: {str(e)}")
    
    def _execute_task(self, task: Task) -> Any:
        """
        执行任务
        
        Args:
            task: 任务对象
            
        Returns:
            任务执行结果
        """
        try:
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.start_time = time.time()
            
            # 执行任务
            if task.timeout:
                # 使用超时
                timer = threading.Timer(task.timeout, self._task_timeout, args=[task])
                timer.start()
                try:
                    result = task.func(*task.args, **task.kwargs)
                finally:
                    timer.cancel()
            else:
                # 直接执行
                result = task.func(*task.args, **task.kwargs)
            
            return result
            
        except Exception as e:
            self.logger.error(f"任务执行错误 - ID: {task.task_id}, 错误: {str(e)}")
            raise
    
    def _task_done_callback(self, future, task: Task) -> None:
        """
        任务完成回调
        
        Args:
            future: Future对象
            task: 任务对象
        """
        try:
            # 获取结果
            task.result = future.result()
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
        finally:
            task.end_time = time.time()
            task.cancel_event.set()
    
    def _task_timeout(self, task: Task) -> None:
        """
        任务超时处理
        
        Args:
            task: 任务对象
        """
        if task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.FAILED
            task.error = "任务执行超时"
            task.cancel_event.set()
    
    def shutdown(self, wait: bool = True) -> None:
        """
        关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        with self.lock:
            if not self.initialized:
                return
            
            self._shutdown_executors()
            self.initialized = False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取线程池统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            # 统计不同状态的任务数量
            status_counts = {status.value: 0 for status in TaskStatus}
            for task in self.tasks.values():
                status_counts[task.status.value] += 1
            
            return {
                'max_workers': self.max_workers,
                'io_bound_workers': self.io_bound_workers,
                'cpu_bound_workers': self.cpu_bound_workers,
                'task_status_counts': status_counts,
                'total_tasks_created': self.task_count,
                'active_tasks': len(self.tasks)
            }
            
    def get_io_active_count(self) -> int:
        """
        获取当前活动的IO线程数量
        
        Returns:
            活动IO线程数量
        """
        if hasattr(self, 'io_executor') and self.io_executor:
            return len(self.io_executor._threads)
        return 0
        
    def get_cpu_active_count(self) -> int:
        """
        获取当前活动的CPU线程数量
        
        Returns:
            活动CPU线程数量
        """
        if hasattr(self, 'cpu_executor') and self.cpu_executor:
            return len(self.cpu_executor._threads)
        return 0
        
    def get_task_count(self) -> int:
        """
        获取总任务数
        
        Returns:
            总任务数
        """
        return self.task_count
        
    def get_completed_task_count(self) -> int:
        """
        获取已完成任务数
        
        Returns:
            已完成任务数
        """
        with self.lock:
            return sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED)

# 创建全局线程池执行器实例
thread_pool = EnhancedThreadPoolExecutor() 