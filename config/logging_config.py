#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置文件
统一管理项目的日志配置
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logging(log_level: Optional[str] = None, log_file: Optional[str] = None):
    """
    设置日志配置
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为None则自动生成
    """
    # 获取配置
    if log_level is None:
        try:
            # 避免循环导入，直接从环境变量获取
            log_level = os.getenv("LOG_LEVEL", "INFO")
        except:
            log_level = "INFO"
    
    # 确保logs目录存在
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # 生成日志文件名
    if log_file is None:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = logs_dir / f"mediacrawler_{today}.log"
    else:
        log_file = Path(log_file)
    
    # 转换日志级别
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    level = level_map.get(log_level.upper(), logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 创建项目专用logger
    logger = logging.getLogger("MediaCrawler")
    logger.setLevel(level)
    
    # 记录日志系统初始化
    logger.info(f"日志系统初始化完成")
    logger.info(f"日志级别: {log_level}")
    logger.info(f"日志文件: {log_file}")
    
    return logger


def get_logger(name: str = "MediaCrawler"):
    """
    获取logger实例
    
    Args:
        name: logger名称
    
    Returns:
        logging.Logger: logger实例
    """
    return logging.getLogger(name)


def log_task_start(task_id: str, platform: str, keywords: str):
    """记录任务开始日志"""
    logger = get_logger()
    logger.info(f"任务开始 - ID: {task_id}, 平台: {platform}, 关键词: {keywords}")


def log_task_complete(task_id: str, platform: str, result_count: int):
    """记录任务完成日志"""
    logger = get_logger()
    logger.info(f"任务完成 - ID: {task_id}, 平台: {platform}, 结果数量: {result_count}")


def log_task_error(task_id: str, platform: str, error: str):
    """记录任务错误日志"""
    logger = get_logger()
    logger.error(f"任务错误 - ID: {task_id}, 平台: {platform}, 错误: {error}")


def log_api_request(method: str, path: str, status_code: int, duration: float):
    """记录API请求日志"""
    logger = get_logger()
    logger.info(f"API请求 - {method} {path} {status_code} {duration:.3f}s")


def log_database_operation(operation: str, table: str, duration: float):
    """记录数据库操作日志"""
    logger = get_logger()
    logger.debug(f"数据库操作 - {operation} {table} {duration:.3f}s")


def log_proxy_usage(proxy_id: str, platform: str, success: bool, duration: float):
    """记录代理使用日志"""
    logger = get_logger()
    status = "成功" if success else "失败"
    logger.info(f"代理使用 - ID: {proxy_id}, 平台: {platform}, {status}, 耗时: {duration:.3f}s")


# 初始化日志系统
if __name__ == "__main__":
    setup_logging()
