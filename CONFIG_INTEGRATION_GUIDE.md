# MediaCrawler 配置集成指南

## 配置系统重构说明

### 🔧 重构目标
- 统一配置管理：MinIO配置使用`config_storage.yaml`，Redis配置使用`config_local.yaml`
- 环境变量支持：根据`ENV`环境变量读取不同配置文件
- Conda环境标准化：使用`mediacrawler`环境
- 依赖包管理：更新`requirements.txt`

### 📁 配置文件结构
```
config/
├── config_local.yaml      # 开发环境配置（包含Redis配置）
├── config_storage.yaml    # 存储配置（MinIO、文件管理）
├── config_production.yaml # 生产环境配置（未来使用）
└── config_manager.py      # 配置管理器
```

### 🎯 主要更改

#### 1. 配置管理器增强 (`config/config_manager.py`)
- ✅ 新增`RedisConfig`配置模型
- ✅ 新增`get_redis_config()`方法
- ✅ 新增`_load_storage_config()`方法
- ✅ 支持从`config_storage.yaml`加载存储配置
- ✅ 支持从`config_local.yaml`加载Redis配置
- ✅ 环境变量优先级支持

#### 2. Redis管理器优化 (`utils/redis_manager.py`)
- ✅ 使用配置管理器获取Redis配置
- ✅ 支持连接池配置
- ✅ 使用配置化的TTL时间
- ✅ 支持Redis密码和高级配置
- ✅ 修复连接池参数问题

#### 3. MinIO服务优化 (`services/minio_service.py`)
- ✅ 使用配置管理器获取存储配置
- ✅ 支持MinIO启用/禁用控制
- ✅ 使用配置化的文件大小阈值
- ✅ 支持配置化的MinIO连接参数

#### 4. 环境配置文件 (`config/config_local.yaml`)
- ✅ 新增Redis配置部分
- ✅ 完整的Redis连接配置
- ✅ 任务结果缓存配置
- ✅ 会话缓存配置

#### 5. .cursorrules文件更新
- ✅ 新增开发环境配置段
- ✅ 明确Conda环境使用规范
- ✅ 配置文件读取规则说明
- ✅ 服务依赖配置说明

#### 6. requirements.txt更新
- ✅ 新增`python-multipart==0.0.6`（文件上传支持）
- ✅ 更新`opencv-python-headless==4.8.1.78`（版本固定）
- ✅ 新增`apscheduler==3.10.4`（任务调度）

### 🚀 使用方式

#### 环境变量设置
```bash
# 设置环境类型
export ENV=local  # 开发环境
# export ENV=production  # 生产环境
```

#### Conda环境激活
```bash
conda activate mediacrawler
```

#### 配置文件优先级
1. **环境变量** (最高优先级)
2. **config_local.yaml** (开发环境)
3. **config_storage.yaml** (存储配置)
4. **默认配置** (最低优先级)

### 📊 配置示例

#### Redis配置示例
```yaml
# config/config_local.yaml
redis:
  host: "localhost"
  port: 6379
  db: 0
  password: ""
  connection_pool_size: 10
  max_connections: 100
  socket_timeout: 5
  socket_connect_timeout: 5
  socket_keepalive: true
  health_check_interval: 30
  retry_on_timeout: true
  task_result_ttl: 604800  # 7天
  task_result_key_prefix: "mediacrawler:task:"
  session_ttl: 3600  # 1小时
  session_key_prefix: "mediacrawler:session:"
```

#### MinIO配置示例
```yaml
# config/config_storage.yaml
storage:
  enable_minio: true
  minio_endpoint: "192.168.31.231:9000"
  minio_access_key: "minioadmin"
  minio_secret_key: "your_minio_password_123"
  minio_secure: false
  minio_bucket: "mediacrawler-videos"
  small_file_threshold: 10485760  # 10MB
```

### 🔍 配置验证

#### 配置系统测试
```bash
conda activate mediacrawler
python -c "
import os
os.environ['ENV'] = 'local'
from config.config_manager import config_manager
from utils.redis_manager import TaskResultRedisManager
from services.minio_service import MinIOService

# 测试Redis配置
redis_config = config_manager.get_redis_config()
print(f'Redis: {redis_config.host}:{redis_config.port}')

# 测试存储配置
storage_config = config_manager.get_storage_config()
print(f'MinIO: {storage_config.minio_endpoint}')

# 测试服务初始化
redis_manager = TaskResultRedisManager()
minio_service = MinIOService()
print('✅ 配置系统正常工作')
"
```

### 🎉 验证结果

```
🔧 配置系统测试
==================================================
📡 Redis配置:
  - 主机: localhost
  - 端口: 6379
  - 数据库: 0
  - 任务结果TTL: 604800秒
💾 存储配置:
  - MinIO启用: True
  - MinIO地址: 192.168.31.231:9000
  - MinIO桶名: mediacrawler-videos
  - 文件大小阈值: 10485760 bytes
✅ Redis管理器初始化成功
✅ MinIO服务初始化成功，可用性: True
==================================================
🎉 配置系统测试完成
```

### 📝 注意事项

1. **环境变量优先级**：环境变量始终具有最高优先级，可以覆盖配置文件设置
2. **配置文件命名**：必须严格按照`config_{ENV}.yaml`格式命名
3. **MinIO配置**：存储相关配置统一放在`config_storage.yaml`中
4. **Redis配置**：缓存相关配置放在对应环境的配置文件中
5. **密码安全**：生产环境中敏感信息应使用环境变量设置

### 🔗 相关文件

- `config/config_manager.py` - 配置管理器
- `config/config_local.yaml` - 开发环境配置
- `config/config_storage.yaml` - 存储配置
- `utils/redis_manager.py` - Redis管理器
- `services/minio_service.py` - MinIO服务
- `requirements.txt` - 依赖包列表
- `.cursorrules` - 项目规则文件

### 🎯 下一步计划

1. **生产环境配置**：创建`config_production.yaml`
2. **配置模板**：创建配置文件模板
3. **环境检测**：增强环境自动检测
4. **配置验证**：添加配置参数验证
5. **热重载**：支持配置文件热重载功能

---

> 📋 **提示**：使用此配置系统时，请确保：
> - 已激活`mediacrawler` Conda环境
> - 已设置正确的`ENV`环境变量
> - 配置文件格式正确且完整
> - Redis和MinIO服务正常运行 