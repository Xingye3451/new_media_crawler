# MediaCrawler 配置迁移指南

## 概述

本文档介绍如何从旧版配置文件迁移到新的统一配置结构。新的配置系统提供了更好的组织性、可扩展性和环境隔离。

## 配置结构变化

### 1. 新增配置模块

新的配置系统包含以下主要模块：

- **代理配置** (`proxy`): 代理服务器设置
- **爬虫配置** (`crawler`): 爬虫行为控制
- **数据库配置** (`database`): 数据库连接设置
- **Redis配置** (`redis`): 缓存和会话管理
- **应用配置** (`app`): 应用基础设置
- **远程桌面配置** (`remote_desktop`): VNC连接设置
- **存储配置** (`storage`): 文件存储管理
- **服务配置** (`server`): Web服务设置
- **安全配置** (`security`): 安全相关设置
- **爬虫服务配置** (`crawler_service`): 爬虫服务管理
- **任务管理配置** (`task_management`): 任务队列管理
- **性能优化配置** (`performance`): 性能调优设置
- **监控配置** (`monitoring`): 系统监控设置
- **开发环境配置** (`development`): 开发工具设置
- **平台特定配置**: 各平台的专用设置

### 2. 环境隔离

新的配置系统支持多环境配置：

- `config_local.yaml`: 本地开发环境
- `config_dev.yaml`: 开发环境
- `config_docker.yaml`: Docker容器环境
- `config_prod.yaml`: 生产环境

## 迁移步骤

### 步骤1: 备份现有配置

```bash
# 备份现有配置文件
cp config/config_local.yaml config/config_local.yaml.backup
cp config/config_dev.yaml config/config_dev.yaml.backup
cp config/config_docker.yaml config/config_docker.yaml.backup
cp config/config_prod.yaml config/config_prod.yaml.backup
```

### 步骤2: 更新配置文件

#### 2.1 本地环境配置

```bash
# 复制模板到本地环境
cp config/config_template.yaml config/config_local.yaml
```

然后根据你的本地环境修改以下关键配置：

```yaml
# 数据库配置
database:
  host: "你的数据库主机"
  port: 3306
  username: "你的用户名"
  password: "你的密码"
  database: "mediacrawler"
  charset: "utf8mb4"

# 爬虫配置
crawler:
  platform: "xhs"  # 选择目标平台
  keywords: "你的关键词"
  max_notes_count: 20  # 根据资源情况调整
  enable_comments: false  # 建议关闭以减少资源消耗
  max_concurrency: 2  # 根据系统性能调整
```

#### 2.2 开发环境配置

```bash
# 复制模板到开发环境
cp config/config_template.yaml config/config_dev.yaml
```

开发环境建议配置：

```yaml
# 开发环境优化配置
crawler:
  max_notes_count: 50  # 开发环境适中设置
  enable_comments: true  # 开发时可以开启
  headless: false  # 显示浏览器便于调试

app:
  debug: true
  log_level: "DEBUG"

development:
  enable_hot_reload: true
  enable_debug_toolbar: true
  enable_detailed_errors: true
```

#### 2.3 Docker环境配置

```bash
# 复制模板到Docker环境
cp config/config_template.yaml config/config_docker.yaml
```

Docker环境配置要点：

```yaml
# Docker环境配置
database:
  host: "${DB_HOST:-192.168.31.231}"  # 使用环境变量
  username: "${DB_USER:-aiuser}"
  password: "${DB_PASSWORD:-edcghj98578}"

remote_desktop:
  enabled: ${REMOTE_DESKTOP_ENABLED:-true}
  vnc_url: "${VNC_URL:-http://localhost:6080/vnc.html}"

storage:
  local_base_path: "/app/data"  # 容器内路径
```

#### 2.4 生产环境配置

```bash
# 复制模板到生产环境
cp config/config_template.yaml config/config_prod.yaml
```

生产环境配置要点：

```yaml
# 生产环境优化配置
crawler:
  max_notes_count: 500  # 生产环境增加数量
  headless: true  # 无头模式
  max_concurrency: 3  # 多线程

app:
  debug: false
  log_level: "INFO"

security:
  enable_api_auth: true  # 启用API认证
  api_key: "${API_KEY:-prod-api-key}"

storage:
  enable_minio: true  # 启用MinIO存储
  cleanup:
    enabled: true  # 启用文件清理
```

### 步骤3: 验证配置

#### 3.1 检查配置语法

```bash
# 验证YAML语法
python -c "import yaml; yaml.safe_load(open('config/config_local.yaml'))"
```

#### 3.2 测试配置加载

```python
# 测试配置加载
from config.env_config_loader import config_loader

# 加载配置
config = config_loader.load_config()

# 验证关键配置
print(f"数据库主机: {config['database']['host']}")
print(f"爬虫平台: {config['crawler']['platform']}")
print(f"Redis主机: {config['redis']['host']}")
```

### 步骤4: 更新代码引用

如果你的代码中有直接引用旧配置的地方，需要更新为新的配置结构：

#### 旧配置引用
```python
# 旧方式
from config.base_config import PLATFORM, KEYWORDS
```

#### 新配置引用
```python
# 新方式
from config.env_config_loader import config_loader

config = config_loader.load_config()
platform = config['crawler']['platform']
keywords = config['crawler']['keywords']
```

## 配置优化建议

### 1. 资源优化

根据你的系统资源调整以下配置：

```yaml
# 内存优化
redis:
  connection_pool_size: 5  # 减少连接池大小
  max_connections: 20  # 减少最大连接数

crawler:
  max_concurrency: 2  # 控制并发数
  max_notes_count: 20  # 控制爬取数量

storage:
  max_concurrent_downloads: 3  # 控制下载并发
```

### 2. 性能优化

```yaml
# 性能优化
performance:
  enable_cache: true
  cache_size_limit: 100
  enable_compression: true
  enable_async: true

monitoring:
  enable_system_monitor: true
  enable_alerts: true
```

### 3. 安全配置

```yaml
# 安全配置
security:
  enable_https: true  # 生产环境启用HTTPS
  enable_api_auth: true
  session_secret: "${SESSION_SECRET}"  # 使用环境变量
```

## 环境变量配置

### 本地环境

```bash
export ENV=local
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_password
```

### Docker环境

```bash
# docker-compose.yml
environment:
  - ENV=docker
  - DB_HOST=192.168.31.231
  - DB_USER=aiuser
  - DB_PASSWORD=edcghj98578
  - VNC_URL=http://localhost:6080/vnc.html
```

### 生产环境

```bash
# 生产环境变量
export ENV=production
export DB_HOST=prod-db.example.com
export DB_USER=prod_user
export DB_PASSWORD=prod_password
export API_KEY=your_production_api_key
export SESSION_SECRET=your_production_session_secret
```

## 故障排除

### 1. 配置加载失败

```bash
# 检查配置文件语法
python -c "import yaml; yaml.safe_load(open('config/config_local.yaml'))"
```

### 2. 环境变量未生效

```bash
# 检查环境变量
echo $ENV
echo $DB_HOST
```

### 3. 配置值获取错误

```python
# 调试配置加载
from config.env_config_loader import config_loader

config = config_loader.load_config()
print("当前环境:", config_loader.get_environment())
print("数据库配置:", config.get('database', {}))
```

## 回滚方案

如果新配置出现问题，可以快速回滚：

```bash
# 恢复备份配置
cp config/config_local.yaml.backup config/config_local.yaml
cp config/config_dev.yaml.backup config/config_dev.yaml
cp config/config_docker.yaml.backup config/config_docker.yaml
cp config/config_prod.yaml.backup config/config_prod.yaml
```

## 总结

新的配置系统提供了：

1. **更好的组织性**: 按功能模块分组配置
2. **环境隔离**: 不同环境使用不同配置文件
3. **类型安全**: 使用数据类定义配置结构
4. **扩展性**: 易于添加新的配置项
5. **向后兼容**: 保持与旧配置的兼容性

通过遵循本指南，你可以顺利迁移到新的配置系统，享受更好的配置管理体验。 