import subprocess
import threading
import time
import psutil
import os
import logging

# ======= 配置项 =======
SOFFICE_PATH = "/usr/bin/soffice"  # 修改为你的LibreOffice路径
PORT = 2002  # LibreOffice监听端口
CHECK_INTERVAL = 3  # 检查周期（秒）
LOG_DIR = "/tmp/soffice_guard_logs"

# 启动命令（保持服务常驻监听）
SOFFICE_CMD = [
    SOFFICE_PATH,
    '--headless',
    f'--accept=socket,host=127.0.0.1,port={PORT};urp;',
    '--nologo',
    '--nofirststartwizard'
]

# ======= 日志配置 =======
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "guard.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("soffice.guard")


def is_soffice_running():
    """检查soffice服务是否存活"""
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            name = proc.info['name']
            cmdline = proc.info['cmdline']
            if name and 'soffice' in name.lower() and '--headless' in ' '.join(cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def start_soffice():
    """启动LibreOffice headless 服务"""
    logger.info("尝试启动 LibreOffice headless 服务...")
    stdout_path = os.path.join(LOG_DIR, "soffice_stdout.log")
    stderr_path = os.path.join(LOG_DIR, "soffice_stderr.log")

    with open(stdout_path, "a") as out, open(stderr_path, "a") as err:
        subprocess.Popen(
            SOFFICE_CMD,
            stdout=out,
            stderr=err,
            start_new_session=True  # 保证其独立于父进程
        )
    logger.info("LibreOffice 已启动，日志输出到 %s", LOG_DIR)


def guard_loop():
    """持续守护soffice服务"""
    logger.info("启动 LibreOffice 守护进程，检查周期: %ds", CHECK_INTERVAL)
    try:
        while True:
            if not is_soffice_running():
                logger.warning("检测到 LibreOffice 服务未运行，准备重启...")
                start_soffice()
                time.sleep(5)  # 启动后稍作等待
            else:
                logger.debug("LibreOffice 服务运行正常")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("守护进程终止")
    except Exception as e:
        logger.exception("守护进程异常退出: %s", e)
def start_guard_daemon():
    t = threading.Thread(target=guard_loop, daemon=True)
    t.start()

if __name__ == "__main__":
    guard_loop()
