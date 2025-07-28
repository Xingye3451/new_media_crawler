# MediaCrawler 优化指南

## 🎯 概述

本文档介绍如何优化 MediaCrawler 爬虫系统，避免服务阻塞，提高运行稳定性。

## 🚨 问题背景

爬虫运行时可能出现以下问题：
- 服务完全阻塞，网页无法刷新
- CPU/内存使用率过高
- 网络连接超时
- 数据库连接池耗尽

## 🔧 优化措施

### 1. 资源管理优化

#### 并发控制
- **限制并发数**: 建议设置为 2-3
- **分批处理**: 每批处理 3-5 个任务
- **超时控制**: 每个批次设置 60-120 秒超时

#### 内存管理
- **减少爬取数量**: 建议 20-30 条
- **关闭不必要功能**: 评论、图片下载
- **增加睡眠间隔**: 建议 5 秒

#### 网络优化
- **限制请求频率**: 批次间增加间隔
- **错误重试机制**: 避免无限重试
- **连接池管理**: 减少 Redis/数据库连接数

### 2. 平台特定优化

#### 小红书 (XHS)
```yaml
crawler:
  platform: xhs
  max_concurrency: 2
  max_notes_count: 20
  enable_comments: false
  enable_images: false
  max_sleep_sec: 5
```

#### 抖音 (DY)
```yaml
crawler:
  platform: dy
  max_concurrency: 1-2  # 反爬较强，建议降低
  max_notes_count: 10-20
  max_sleep_sec: 8  # 增加睡眠间隔
```

#### 快手 (KS)
```yaml
crawler:
  platform: ks
  max_concurrency: 2-3
  max_notes_count: 20-30
  enable_comments: false  # 评论获取较慢
```

#### B站 (BILI)
```yaml
crawler:
  platform: bili
  max_concurrency: 2-3
  max_notes_count: 20-30
  enable_comments: false
```

### 3. 监控工具

#### 资源监控
```bash
# 启动资源监控
python monitor_resources.py

# 监控指标
- CPU使用率 > 80%: 警告
- 内存使用率 > 85%: 警告  
- 磁盘使用率 > 90%: 警告
```

#### 紧急停止
```bash
# 紧急停止所有爬虫
./emergency_stop.sh

# 手动停止
pkill -f "python.*main.py"
pkill -f "python.*crawler"
```

### 4. 配置优化

#### 推荐配置
```yaml
crawler:
  max_concurrency: 2
  max_notes_count: 20
  enable_comments: false
  enable_images: false
  max_sleep_sec: 5

redis:
  connection_pool_size: 5
  max_connections: 20

app:
  log_level: "INFO"
```

## 📊 监控指标

### 正常范围
- **CPU使用率**: < 60%
- **内存使用率**: < 70%
- **磁盘使用率**: < 80%
- **网络延迟**: < 100ms

### 警告阈值
- **CPU使用率**: > 80%
- **内存使用率**: > 85%
- **磁盘使用率**: > 90%

### 紧急阈值
- **CPU使用率**: > 95%
- **内存使用率**: > 95%
- **磁盘使用率**: > 95%

## 🛠️ 故障排除

### 1. 服务阻塞
```bash
# 立即停止
./emergency_stop.sh

# 检查进程
ps aux | grep python

# 检查资源
htop
free -h
df -h
```

### 2. 内存泄漏
```bash
# 检查内存使用
ps aux --sort=-%mem | head -10

# 重启服务
./emergency_stop.sh
python main.py
```

### 3. 网络超时
```bash
# 检查网络连接
ping 192.168.31.231

# 检查端口
telnet 192.168.31.231 3306
telnet 192.168.31.231 6379
```

### 4. 数据库连接问题
```bash
# 检查数据库连接
mysql -h 192.168.31.231 -u root -p

# 检查连接数
SHOW PROCESSLIST;
```

## 📈 性能调优

### 1. 系统级优化
```bash
# 增加文件描述符限制
ulimit -n 65536

# 优化内核参数
echo 'net.core.somaxconn = 65535' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_max_syn_backlog = 65535' >> /etc/sysctl.conf
sysctl -p
```

### 2. 数据库优化
```sql
-- 优化MySQL配置
SET GLOBAL max_connections = 200;
SET GLOBAL innodb_buffer_pool_size = 1073741824;  -- 1GB
SET GLOBAL query_cache_size = 67108864;  -- 64MB
```

### 3. Redis优化
```bash
# 优化Redis配置
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## 🔄 最佳实践

### 1. 运行前检查
- [ ] 检查系统资源
- [ ] 验证网络连接
- [ ] 确认数据库状态
- [ ] 备份重要数据

### 2. 运行中监控
- [ ] 启动资源监控
- [ ] 观察日志输出
- [ ] 检查错误信息
- [ ] 监控系统资源

### 3. 运行后清理
- [ ] 停止监控脚本
- [ ] 清理临时文件
- [ ] 检查数据完整性
- [ ] 备份爬取结果

## 📝 使用示例

### 1. 基础使用
```bash
# 1. 启动资源监控
python monitor_resources.py &

# 2. 运行爬虫
python main.py

# 3. 监控运行状态
tail -f logs/crawler.log
```

### 2. 多平台测试
```bash
# 小红书测试
python main.py --platform xhs --keywords "美食"

# 抖音测试  
python main.py --platform dy --keywords "旅游"

# B站测试
python main.py --platform bili --keywords "编程"
```

### 3. 性能测试
```bash
# 小规模测试
python main.py --max-count 5 --concurrency 1

# 中等规模测试
python main.py --max-count 20 --concurrency 2

# 大规模测试
python main.py --max-count 50 --concurrency 3
```

## ⚠️ 注意事项

1. **遵守平台规则**: 不要过度爬取，遵守robots.txt
2. **合理控制频率**: 避免对目标平台造成压力
3. **监控资源使用**: 及时发现问题并处理
4. **备份重要数据**: 定期备份爬取结果
5. **遵守法律法规**: 仅用于学习研究目的

## 🆘 紧急联系

如果遇到严重问题：
1. 立即执行 `./emergency_stop.sh`
2. 检查系统资源状态
3. 查看错误日志
4. 联系技术支持

---

**最后更新**: 2024年1月
**版本**: v1.0
**维护者**: MediaCrawler Team 