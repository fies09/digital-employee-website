#!/usr/bin/env python
# -*- coding = utf-8 -*-
import logging
import os
import random
import sys
from datetime import datetime
import pytz
from pathlib import Path
from logging import Handler
from logging.handlers import RotatingFileHandler

# 设置时区为你需要的时区，例如 'Asia/Shanghai'
local_tz = pytz.timezone('Asia/Shanghai')


class TimezoneFormatter(logging.Formatter):
    """自定义日志格式化器以调整日志时间到指定时区"""
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)  # 从 UTC 转换
        return dt.astimezone(local_tz)  # 将时间转换为指定时区

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            s = dt.strftime("%Y-%m-%d %H:%M:%S")
        return s

# 显示方式: 0（默认\）、1（高亮）、22（非粗体）、4（下划线）、24（非下划线）、 5（闪烁）、25（非闪烁）、7（反显）、27（非反显）
# 前景色:   30（黑色）、31（红色）、32（绿色）、 33（黄色）、34（蓝色）、35（洋 红）、36（青色）、37（白色）
# 背景色:   40（黑色）、41（红色）、42（绿色）、 43（黄色）、44（蓝色）、45（洋 红）、46（青色）、47（白色）

fcolor = [
    '\033[32m',
    '\033[33m',
    '\033[36m',
]


class StreamHandler(Handler):
    terminator = '\n'
    cur_color = '\033[33m'
    err_color = '\033[1;31;40m'

    def __init__(self, stream=None):
        Handler.__init__(self)
        if stream is None:
            stream = sys.stderr
        self.stream = stream

    def flush(self):
        self.acquire()
        try:
            if self.stream and hasattr(self.stream, "flush"):
                self.stream.flush()
        finally:
            self.release()

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if record.levelno >= logging.ERROR:
                cr = self.err_color
            else:
                cr = self._get_color(msg)

            stream.write(cr + msg + '\033[0m')
            stream.write(self.terminator)
            self.flush()

        except Exception:
            self.handleError(record)

    def _get_color(self, msg):
        if '[+]' in msg:
            num = random.randint(1, len(fcolor)) - 1
            while self.cur_color == fcolor[num]:
                num = random.randint(1, len(fcolor)) - 1
            self.cur_color = fcolor[num]

        return self.cur_color


# 设置 log_path 为项目根目录下的 logs 目录
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
log_path = os.path.join(project_root, 'logs')
if not os.path.exists(log_path):
    # 如果路径不存在，则创建路径
    os.makedirs(log_path, exist_ok=True)

# 设置时区为 'Asia/Shanghai'
local_tz = pytz.timezone('Asia/Shanghai')

# 获得当前时间，使用指定的时区
now = datetime.now(local_tz)

# 转换为指定的格式
log_time = now.strftime("%Y_%m_%d")
log_name = str(log_time)
fn = os.path.join(log_path, log_name + '.log')
if os.path.exists(fn):
    if os.path.getsize(fn) > 0:
        # 文件存在且非空，追加内容
        with open(fn, 'a', encoding='utf-8') as f:
            pass
    else:
        # 文件存在但为空，写入内容
        with open(fn, 'w', encoding='utf-8') as f:
            pass
else:
    # 文件不存在，创建文件并写入内容
    with open(fn, 'w', encoding='utf-8') as f:
        pass

logger = logging.getLogger(log_name)
logger.setLevel(level=logging.INFO)


# 设置时区格式器
formatter = TimezoneFormatter('%(asctime)s - %(filename)s - line:%(lineno)s - %(levelname)s| %(message)s')

# 替换原始的 filehandler 格式化器
filehandler = RotatingFileHandler(fn, maxBytes=5120000, backupCount=10, encoding="utf-8")
filehandler.setLevel(level=logging.INFO)
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)


# console 同样使用时区格式化器
consoleformatter = TimezoneFormatter('%(asctime)s | %(levelname)5s | %(message)s - [%(filename)s - %(lineno)s]')
if os.environ.setdefault('PY_ENV', 'dev') == 'dev':
    consoleformatter = TimezoneFormatter('%(asctime)s | %(levelname)5s | %(message)s - [%(filename)s - %(lineno)s]')

console = StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(consoleformatter)
logger.addHandler(console)


# terminal 也同样设置
tf = TimezoneFormatter('%(asctime)s - %(filename)s - line:%(lineno)s - %(levelname)s| %(message)s')
if os.environ.setdefault('PY_ENV', 'dev') == 'dev':
    tf = TimezoneFormatter('\t[!] %(asctime)s | [%(processName)s : %(threadName)s] - [%(filename)s - %(lineno)s]')

terminal = StreamHandler()
terminal.setLevel(logging.ERROR)
terminal.setFormatter(tf)
logger.addHandler(terminal)

# 关闭日志输出
# logging.getLogger("paramiko").setLevel(logging.ERROR)
# logging.getLogger('werkzeug').setLevel(logging.ERROR)
# logging.getLogger('apscheduler').setLevel(logging.ERROR)
logging.getLogger("paramiko").setLevel(logging.INFO)
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.INFO)

__all__ = ['logger']