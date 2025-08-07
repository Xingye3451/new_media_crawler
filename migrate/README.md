# MediaCrawler Database Migration System

## 概述

MediaCrawler 数据库迁移系统提供了完整的数据库版本管理功能，支持全量迁移和增量迁移，确保数据库结构的版本控制和一致性。

## 目录结构

```
migrate/
├── full/                    # 全量迁移
│   ├── ddl/                # 数据定义语言
│   │   └── v1.0.0/        # 版本目录
│   │       └── 01_create_tables.sql
│   └── dml/                # 数据操作语言
│       └── v1.0.0/
├── incremental/             # 增量迁移
│   ├── ddl/                # 数据定义语言
│   │   └── v1.0.0/        # 版本目录
│   └── dml/                # 数据操作语言
│       └── v1.0.0/
├── migrate.py              # 迁移工具脚本
└── README.md               # 本文档
```

## 版本说明

### v1.0.0 (当前版本)

**全量迁移包含的表结构：**

1. **unified_content** - 统一内容表（核心表）
   - 存储所有平台的内容数据
   - 支持视频、图片、文本等多种内容类型
   - 包含作者信息、统计数据、存储信息等

2. **unified_creator** - 统一创作者表
   - 存储所有平台的创作者信息
   - 包含粉丝数、认证状态、等级等信息

3. **unified_comment** - 统一评论表
   - 存储所有平台的评论数据
   - 支持层级评论结构

4. **crawler_tasks** - 爬虫任务表
   - 管理爬虫任务的执行状态
   - 支持多种爬取类型和参数配置

5. **crawler_task_logs** - 任务日志表
   - 记录爬虫任务的执行日志
   - 支持不同日志级别和进度跟踪

6. **social_accounts** - 社交账号表
   - 管理各平台的登录账号
   - 支持多种登录方式

7. **login_tokens** - 登录令牌表
   - 存储登录会话和令牌信息
   - 支持令牌过期管理

8. **login_sessions** - 登录会话表
   - 管理用户登录会话
   - 支持会话过期和状态管理

9. **proxy_pool** - 代理池表
   - 管理代理服务器信息
   - 支持代理质量评估和状态监控

10. **platforms** - 平台配置表
    - 存储各平台的配置信息
    - 支持平台启用/禁用管理

11. **task_statistics** - 任务统计表
    - 记录任务执行统计信息
    - 支持性能分析和监控

12. **video_download_tasks** - 视频下载任务表
    - 管理视频文件下载任务
    - 支持下载进度跟踪和错误处理

13. **video_files** - 视频文件表
    - 管理下载的视频文件信息
    - 支持本地和MinIO存储

14. **video_statistics** - 视频统计表
    - 记录视频相关统计信息
    - 支持数据分析和报表

15. **video_storage_stats** - 存储统计表
    - 监控存储空间使用情况
    - 支持存储容量管理

## 使用方法

### 1. 检查数据库状态

```bash
python migrate/migrate.py --check
```

### 2. 查看迁移计划（干运行）

```bash
python migrate/migrate.py --dry-run --type full --version v1.0.0
```

### 3. 执行全量迁移

```bash
# 基本迁移
python migrate/migrate.py --type full --version v1.0.0

# 带备份的迁移
python migrate/migrate.py --type full --version v1.0.0 --backup

# 指定配置文件的迁移
python migrate/migrate.py --config config/config_prod.yaml --type full --version v1.0.0
```

### 4. 执行增量迁移

```bash
python migrate/migrate.py --type incremental --version v1.0.1
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config` | 配置文件路径 | `config/config_local.yaml` |
| `--type` | 迁移类型 (full/incremental) | `full` |
| `--version` | 迁移版本 | `v1.0.0` |
| `--backup` | 迁移前创建备份 | `False` |
| `--backup-path` | 备份目录路径 | `./backups` |
| `--check` | 检查数据库状态 | `False` |
| `--dry-run` | 干运行（显示执行计划） | `False` |

## 配置文件要求

迁移工具需要从配置文件中读取数据库连接信息：

```yaml
database:
  host: "192.168.31.231"
  port: 3306
  username: "aiuser"
  password: "edcghj98578"
  database: "mediacrawler"
  charset: "utf8mb4"
```

## 依赖要求

```bash
pip install mysql-connector-python pyyaml
```

## 安全注意事项

1. **备份重要**：在生产环境执行迁移前，务必创建数据库备份
2. **权限控制**：确保数据库用户具有足够的权限执行DDL操作
3. **测试环境**：建议先在测试环境验证迁移脚本
4. **版本控制**：迁移文件应纳入版本控制系统

## 故障排除

### 常见问题

1. **连接失败**
   - 检查数据库配置信息
   - 确认数据库服务运行状态
   - 验证网络连接

2. **权限错误**
   - 确认数据库用户具有CREATE、ALTER、DROP权限
   - 检查数据库用户的主机访问限制

3. **字符集问题**
   - 确保数据库支持utf8mb4字符集
   - 检查表创建语句的字符集设置

### 日志文件

迁移工具会生成详细的日志文件：
- 控制台输出：实时显示执行状态
- 文件日志：`migrate.log` 包含详细执行记录

## 版本管理规范

### 版本命名

- 格式：`v主版本.次版本.修订版本`
- 示例：`v1.0.0`、`v1.0.1`、`v1.1.0`

### 文件命名

- DDL文件：`01_create_tables.sql`、`02_add_indexes.sql`
- DML文件：`01_insert_initial_data.sql`、`02_update_data.sql`

### 版本升级流程

1. 创建新版本目录
2. 编写迁移脚本
3. 测试迁移脚本
4. 更新文档
5. 执行迁移

## 扩展功能

### 自定义迁移脚本

可以创建自定义的迁移脚本：

```python
from migrate.migrate import DatabaseMigrator

migrator = DatabaseMigrator("config/config_local.yaml")
success = migrator.run_migration("full", "v1.0.0")
```

### 批量迁移

支持批量执行多个版本的迁移：

```bash
# 执行多个版本
for version in v1.0.0 v1.0.1 v1.1.0; do
    python migrate/migrate.py --type incremental --version $version
done
```

## 联系支持

如有问题或建议，请联系开发团队或提交Issue。
