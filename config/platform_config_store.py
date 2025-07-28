#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平台配置存储模块
提供简单的配置保存和加载功能
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from tools import utils

class PlatformConfigStore:
    """平台配置存储类"""
    
    def __init__(self, config_dir: str = "./data/configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._config_cache = {}
    
    def save_config(self, platform: str, config: Dict[str, Any]) -> bool:
        """保存平台配置"""
        try:
            # 添加时间戳
            config['last_updated'] = datetime.now().isoformat()
            config['platform'] = platform
            
            # 保存到文件
            config_file = self.config_dir / f"{platform}_config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # 更新缓存
            self._config_cache[platform] = config
            
            utils.logger.info(f"平台 {platform} 配置已保存")
            return True
            
        except Exception as e:
            utils.logger.error(f"保存平台 {platform} 配置失败: {e}")
            return False
    
    def load_config(self, platform: str) -> Optional[Dict[str, Any]]:
        """加载平台配置"""
        try:
            # 先检查缓存
            if platform in self._config_cache:
                return self._config_cache[platform]
            
            # 从文件加载
            config_file = self.config_dir / f"{platform}_config.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._config_cache[platform] = config
                    return config
            
            return None
            
        except Exception as e:
            utils.logger.error(f"加载平台 {platform} 配置失败: {e}")
            return None
    
    def delete_config(self, platform: str) -> bool:
        """删除平台配置"""
        try:
            # 删除文件
            config_file = self.config_dir / f"{platform}_config.json"
            if config_file.exists():
                config_file.unlink()
            
            # 清除缓存
            if platform in self._config_cache:
                del self._config_cache[platform]
            
            utils.logger.info(f"平台 {platform} 配置已删除")
            return True
            
        except Exception as e:
            utils.logger.error(f"删除平台 {platform} 配置失败: {e}")
            return False
    
    def list_configs(self) -> Dict[str, Any]:
        """列出所有配置"""
        try:
            configs = {}
            for config_file in self.config_dir.glob("*_config.json"):
                platform = config_file.stem.replace("_config", "")
                config = self.load_config(platform)
                if config:
                    configs[platform] = config
            
            return configs
            
        except Exception as e:
            utils.logger.error(f"列出配置失败: {e}")
            return {}
    
    def export_all_configs(self) -> Dict[str, Any]:
        """导出所有配置"""
        try:
            configs = self.list_configs()
            return {
                "configs": configs,
                "export_time": datetime.now().isoformat(),
                "total_platforms": len(configs)
            }
            
        except Exception as e:
            utils.logger.error(f"导出配置失败: {e}")
            return {"configs": {}, "export_time": datetime.now().isoformat(), "total_platforms": 0}
    
    def import_configs(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """导入配置"""
        try:
            imported_count = 0
            failed_platforms = []
            
            for platform, config in configs.items():
                if self.save_config(platform, config):
                    imported_count += 1
                else:
                    failed_platforms.append(platform)
            
            return {
                "imported_count": imported_count,
                "failed_platforms": failed_platforms,
                "total_platforms": len(configs)
            }
            
        except Exception as e:
            utils.logger.error(f"导入配置失败: {e}")
            return {"imported_count": 0, "failed_platforms": list(configs.keys()), "total_platforms": len(configs)}

# 全局配置存储实例
platform_config_store = PlatformConfigStore() 