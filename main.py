# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


import asyncio
import sys

import cmd_arg
import config
import db
from base.base_crawler import AbstractCrawler
from media_platform.bilibili import BilibiliCrawler
from media_platform.douyin import DouYinCrawler
from media_platform.kuaishou import KuaishouCrawler
from media_platform.tieba import TieBaCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.xhs import XiaoHongShuCrawler
from media_platform.zhihu import ZhihuCrawler


class PlatformComingSoonException(Exception):
    """平台即将支持异常"""
    pass


class CrawlerFactory:
    # 视频优先平台 - 当前支持
    VIDEO_PLATFORMS = {
        "xhs": XiaoHongShuCrawler,
        "dy": DouYinCrawler,
        "ks": KuaishouCrawler,
        "bili": BilibiliCrawler,
    }
    
    # 文字平台 - 即将支持
    COMING_SOON_PLATFORMS = {
        "wb": "微博",
        "tieba": "贴吧", 
        "zhihu": "知乎"
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        # 检查是否为即将支持的平台
        if platform in CrawlerFactory.COMING_SOON_PLATFORMS:
            platform_name = CrawlerFactory.COMING_SOON_PLATFORMS[platform]
            raise PlatformComingSoonException(f"{platform_name}平台即将支持，敬请期待！当前专注于短视频平台优化。")
        
        # 检查是否为支持的视频平台
        crawler_class = CrawlerFactory.VIDEO_PLATFORMS.get(platform)
        if not crawler_class:
            raise ValueError("Invalid Media Platform Currently only supported xhs or dy or ks or bili ...")
        return crawler_class()


async def main():
    # parse cmd
    await cmd_arg.parse_cmd()

    # init db
    if config.SAVE_DATA_OPTION == "db":
        await db.init_db()

    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    await crawler.start()

    if config.SAVE_DATA_OPTION == "db":
        await db.close()

    

if __name__ == '__main__':
    try:
        # asyncio.run(main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        sys.exit()
