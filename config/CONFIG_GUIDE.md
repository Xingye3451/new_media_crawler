# MediaCrawler 配置管理系统使用指南

## 概述

MediaCrawler 现在支持多种配置源的管理系统，让配置更加灵活和易于管理。支持环境变量、YAML配置文件、JSON配置文件等多种配置方式。

## 配置源优先级

配置系统按以下优先级加载配置（从高到低）：

1. **环境变量** - 最高优先级，适合敏感信息
2. **YAML配置文件** - 推荐使用，结构清晰
3. **JSON配置文件** - 适合程序化配置
4. **数据库配置** - 动态配置（待实现）
5. **内存配置** - 运行时临时配置

## 环境配置

### 1. 环境变量设置

```bash
# 设置当前环境
export ENV=development  # 可选: development, production, test

# 代理配置
export PROXY_PROVIDER_NAME=qingguo
export ENABLE_IP_PROXY=true
export IP_PROXY_POOL_COUNT=5

# 青果代理配置
export qg_key="your_qingguo_key"
export qg_pwd="your_qingguo_pwd"

# 快代理配置
export kdl_secret_id="your_kuaidaili_secret_id"
export kdl_signature="your_kuaidaili_signature"
export kdl_user_name="your_kuaidaili_username"
export kdl_user_pwd="your_kuaidaili_password"

# 爬虫配置
export PLATFORM=xhs
export KEYWORDS="编程副业,编程兼职"
export CRAWLER_MAX_NOTES_COUNT=100
export ENABLE_GET_COMMENTS=true
export SAVE_DATA_OPTION=json

# 数据库配置
export DB_HOST=localhost
export DB_PORT=3306
export DB_USERNAME=root
export DB_PASSWORD=your_password
export DB_DATABASE=media_crawler

# 应用配置
export DEBUG=false
export LOG_LEVEL=INFO
export DATA_DIR=./data
```

### 2. 配置文件方式

#### YAML配置文件（推荐）

创建 `config/config_development.yaml`：

```yaml
proxy:
  provider_name: "qingguo"
  enabled: true
  pool_count: 5
  validate_ip: true
  qingguo_key: "your_qingguo_key"
  qingguo_pwd: "your_qingguo_pwd"

crawler:
  platform: "xhs"
  keywords: "编程副业,编程兼职"
  login_type: "qrcode"
  crawler_type: "search"
  max_notes_count: 100
  enable_comments: true
  enable_images: false
  save_data_option: "json"
  headless: false
  max_sleep_sec: 2
  max_concurrency: 1

database:
  host: "localhost"
  port: 3306
  username: "root"
  password: "your_password"
  database: "media_crawler"
  charset: "utf8mb4"

app:
  debug: false
  log_level: "INFO"
  data_dir: "./data"
  user_data_dir: "%s_user_data_dir"
```

#### JSON配置文件

创建 `config/config_development.json`：

```json
{
  "proxy": {
    "provider_name": "qingguo",
    "enabled": true,
    "pool_count": 5,
    "validate_ip": true,
    "qingguo_key": "your_qingguo_key",
    "qingguo_pwd": "your_qingguo_pwd"
  },
  "crawler": {
    "platform": "xhs",
    "keywords": "编程副业,编程兼职",
    "login_type": "qrcode",
    "crawler_type": "search",
    "max_notes_count": 100,
    "enable_comments": true,
    "enable_images": false,
    "save_data_option": "json",
    "headless": false,
    "max_sleep_sec": 2,
    "max_concurrency": 1
  },
  "database": {
    "host": "localhost",
    "port": 3306,
    "username": "root",
    "password": "your_password",
    "database": "media_crawler",
    "charset": "utf8mb4"
  },
  "app": {
    "debug": false,
    "log_level": "INFO",
    "data_dir": "./data",
    "user_data_dir": "%s_user_data_dir"
  }
}
```

## 配置管理工具

### 1. 显示当前配置

```bash
# 显示所有配置
python tools/config_tools.py show

# 显示特定配置项
python tools/config_tools.py get proxy.provider_name
python tools/config_tools.py get crawler.platform
```

### 2. 导出配置

```bash
# 导出开发环境配置到YAML
python tools/config_tools.py export development --format yaml

# 导出生产环境配置到JSON
python tools/config_tools.py export production --format json

# 导出测试环境配置
python tools/config_tools.py export test --format yaml
```

### 3. 设置配置

```bash
# 设置代理提供商
python tools/config_tools.py set proxy.provider_name qingguo

# 设置爬虫平台
python tools/config_tools.py set crawler.platform xhs

# 设置最大爬取数量
python tools/config_tools.py set crawler.max_notes_count 200
```

### 4. 重新加载配置

```bash
# 重新加载配置文件
python tools/config_tools.py reload
```

### 5. 创建环境配置

```bash
# 创建开发环境配置文件
python tools/config_tools.py create development

# 创建生产环境配置文件
python tools/config_tools.py create production

# 创建测试环境配置文件
python tools/config_tools.py create test
```

## 环境配置示例

### 开发环境 (development)

```bash
# 设置环境
export ENV=development

# 运行爬虫
python main.py
```

特点：
- 显示浏览器窗口（headless=false）
- 较小的爬取数量
- 较长的请求间隔
- 详细的日志输出

### 生产环境 (production)

```bash
# 设置环境
export ENV=production

# 运行爬虫
python main.py
```

特点：
- 无头模式（headless=true）
- 较大的爬取数量
- 较短的请求间隔
- 多线程并发
- 使用数据库存储

### 测试环境 (test)

```bash
# 设置环境
export ENV=test

# 运行爬虫
python main.py
```

特点：
- 最小的爬取数量
- 关闭代理
- 快速测试模式

## 配置项说明

### 代理配置 (proxy)

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| provider_name | string | "kuaidaili" | 代理提供商：qingguo, kuaidaili, jisuhttp |
| enabled | boolean | false | 是否启用代理 |
| pool_count | int | 5 | 代理池大小 |
| validate_ip | boolean | true | 是否验证代理IP |
| qingguo_key | string | "" | 青果代理Key |
| qingguo_pwd | string | "" | 青果代理密码（可选） |
| kuaidaili_secret_id | string | "" | 快代理Secret ID |
| kuaidaili_signature | string | "" | 快代理签名 |
| kuaidaili_user_name | string | "" | 快代理用户名 |
| kuaidaili_user_pwd | string | "" | 快代理密码 |
| jisu_http_key | string | "" | 极速HTTP代理Key |

### 爬虫配置 (crawler)

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| platform | string | "xhs" | 平台：xhs, dy, ks, bili, wb, tieba, zhihu |
| keywords | string | "编程副业,编程兼职" | 搜索关键词 |
| login_type | string | "qrcode" | 登录类型：qrcode, phone, cookie |
| crawler_type | string | "search" | 爬取类型：search, detail, creator |
| max_notes_count | int | 200 | 最大爬取数量 |
| enable_comments | boolean | true | 是否爬取评论 |
| enable_sub_comments | boolean | false | 是否爬取二级评论 |
| enable_images | boolean | false | 是否爬取图片 |
| save_data_option | string | "json" | 数据保存方式：json, csv, db |
| headless | boolean | false | 是否无头模式 |
| max_sleep_sec | int | 2 | 最大请求间隔（秒） |
| max_concurrency | int | 1 | 最大并发数 |

### 数据库配置 (database)

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| host | string | "localhost" | 数据库主机 |
| port | int | 3306 | 数据库端口 |
| username | string | "root" | 数据库用户名 |
| password | string | "" | 数据库密码 |
| database | string | "media_crawler" | 数据库名称 |
| charset | string | "utf8mb4" | 字符集 |

### 应用配置 (app)

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| debug | boolean | false | 调试模式 |
| log_level | string | "INFO" | 日志级别 |
| data_dir | string | "./data" | 数据目录 |
| user_data_dir | string | "%s_user_data_dir" | 用户数据目录 |

## 最佳实践

### 1. 敏感信息管理

```bash
# 生产环境使用环境变量存储敏感信息
export QINGGUO_KEY="your_actual_key"
export QINGGUO_PWD="your_actual_password"
export DB_PASSWORD="your_db_password"

# 配置文件中使用占位符
qingguo_key: "${QINGGUO_KEY}"
qingguo_pwd: "${QINGGUO_PWD}"
```

### 2. 环境隔离

```bash
# 不同环境使用不同的配置文件
config/
├── config_development.yaml
├── config_production.yaml
└── config_test.yaml
```

### 3. 配置验证

```bash
# 运行前检查配置
python tools/config_tools.py show

# 验证代理配置
python test/test_qingguo_proxy.py
```

### 4. 配置备份

```bash
# 导出当前配置作为备份
python tools/config_tools.py export backup --format yaml

# 定期备份配置文件
cp config/config_*.yaml backup/
```

## 故障排除

### 1. 配置加载失败

```bash
# 检查配置文件语法
python -c "import yaml; yaml.safe_load(open('config/config_development.yaml'))"

# 重新加载配置
python tools/config_tools.py reload
```

### 2. 环境变量未生效

```bash
# 检查环境变量
echo $ENV
echo $PROXY_PROVIDER_NAME

# 重新设置环境变量
export ENV=development
export PROXY_PROVIDER_NAME=qingguo
```

### 3. 代理配置问题

```bash
# 检查代理配置
python tools/config_tools.py get proxy.provider_name
python tools/config_tools.py get proxy.qingguo_key

# 测试代理连接
python test/test_qingguo_proxy.py
```

## 迁移指南

### 从旧版本迁移

1. **备份现有配置**
   ```bash
   cp config/base_config.py config/base_config_backup.py
   ```

2. **创建新的配置文件**
   ```bash
   python tools/config_tools.py create development
   ```

3. **迁移配置项**
   - 将 `base_config.py` 中的配置项迁移到 YAML 文件
   - 敏感信息使用环境变量

4. **测试新配置**
   ```bash
   export ENV=development
   python tools/config_tools.py show
   python main.py
   ```

### 向后兼容

新的配置系统完全向后兼容：
- 原有的 `config/base_config.py` 仍然可以正常工作
- 环境变量配置仍然有效
- 可以逐步迁移到新的配置系统

## 总结

新的配置管理系统提供了：

1. **灵活性**: 支持多种配置源
2. **安全性**: 敏感信息可以通过环境变量管理
3. **可维护性**: 结构化的配置文件
4. **环境隔离**: 不同环境使用不同配置
5. **工具支持**: 完整的配置管理工具
6. **向后兼容**: 不影响现有代码

建议优先使用 YAML 配置文件进行配置管理，敏感信息通过环境变量传递，这样可以既保证配置的灵活性，又确保安全性。 