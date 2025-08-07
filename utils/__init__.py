# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  

import logging
from pathlib import Path
from datetime import datetime

# 导入全局logger
try:
    from tools.utils import logger
except ImportError:
    # 如果无法导入，创建一个默认的logger
    # 确保logs目录存在
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # 生成日志文件名（按日期）
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"mediacrawler_{today}.log"
    
    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s (%(filename)s:%(lineno)d) - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 创建项目专用logger
    logger = logging.getLogger("MediaCrawler")
    logger.setLevel(logging.INFO)
    
    # 记录日志系统初始化
    logger.info(f"日志系统初始化完成，日志文件: {log_file}")

# 导出logger，使其他模块可以通过utils.logger访问
__all__ = ['logger'] 