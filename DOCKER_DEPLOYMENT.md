# MediaCrawler Docker 部署指南

## 概述
MediaCrawler 支持完整的Docker容器化部署，内置VNC远程桌面服务，支持web界面远程操作验证码和登录流程。

## 特性
- 🐳 **完整容器化**：包含API服务、VNC服务器、noVNC Web界面
- 🖥️ **内置远程桌面**：支持浏览器访问VNC界面
- ⚙️ **环境变量配置**：支持灵活的配置管理
- 📦 **一键部署**：使用docker-compose快速启动
- 🔒 **安全访问**：VNC密码保护

## 快速开始

### 1. 构建和启动服务
```bash
# 克隆代码
git clone <repository-url>
cd media_crawler

# 使用docker-compose启动所有服务
docker-compose up -d
```

### 2. 访问服务
- **API服务**: http://localhost:8100
- **VNC Web界面**: http://localhost:6080/vnc.html
- **VNC直连**: localhost:5901 (需要VNC客户端)

### 3. VNC登录
- 默认密码: `mediacrawler123`
- 分辨率: 1280x720
- 颜色深度: 24位

## 配置说明

### 环境变量配置

#### VNC相关配置
```yaml
environment:
  - VNC_PASSWORD=mediacrawler123          # VNC访问密码
  - VNC_URL=http://localhost:6080/vnc.html # noVNC Web地址
  - VNC_HOST=localhost                     # VNC服务器主机
  - VNC_PORT=6080                         # noVNC Web端口
  - DISPLAY_NUMBER=1                      # X11显示器编号
  - REMOTE_DESKTOP_ENABLED=true           # 启用远程桌面功能
```

#### 数据库配置
```yaml
environment:
  - DB_HOST=192.168.31.231                # 数据库主机
  - DB_PORT=3306                          # 数据库端口
  - DB_USER=aiuser                        # 数据库用户名
  - DB_PASSWORD=edcghj98578               # 数据库密码
  - DB_NAME=mediacrawler                  # 数据库名
```

#### 代理配置（可选）
```yaml
environment:
  - QINGGUO_KEY=your_key                  # 青果代理密钥
  - KUAIDAILI_SECRET_ID=your_id           # 快代理ID
  - KUAIDAILI_SIGNATURE=your_signature    # 快代理签名
```

### 外部访问配置

如果需要从外部网络访问VNC，修改docker-compose.yml中的VNC_URL：

```yaml
# 修改为实际的服务器IP地址
- VNC_URL=http://192.168.31.231:6080/vnc.html
```

### 端口映射
```yaml
ports:
  - "8100:8100"    # API服务端口
  - "6080:6080"    # noVNC Web界面端口
  - "5901:5901"    # VNC直连端口
```

## 目录结构
```
media_crawler/
├── docker-compose.yml     # Docker编排文件
├── Dockerfile.api         # API服务Dockerfile
├── config/
│   ├── config_docker.yaml # Docker环境配置
│   └── ...
├── data/                  # 数据目录（挂载到容器）
├── logs/                  # 日志目录（挂载到容器）
└── ...
```

## 使用流程

### 1. 启动远程桌面登录
1. 访问 http://localhost:8100 打开API管理界面
2. 选择账号，点击"🖥️ 远程桌面登录（推荐）"
3. 点击"打开远程桌面完成登录"按钮
4. 在VNC界面中完成完整的登录流程
5. 系统自动检测登录完成并保存cookies

### 2. VNC界面操作
- 在浏览器中打开 http://localhost:6080/vnc.html
- 输入VNC密码（默认：mediacrawler123）
- 进入桌面环境，可以看到自动打开的浏览器
- 在浏览器中完成登录操作

## 服务管理

### 查看容器状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f mediacrawler-api
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart mediacrawler-api
```

### 停止服务
```bash
docker-compose down
```

### 重新构建镜像
```bash
docker-compose build --no-cache
docker-compose up -d
```

## 故障排除

### VNC连接问题
1. **无法访问VNC界面**
   ```bash
   # 检查容器是否正常运行
   docker-compose ps
   
   # 检查端口是否正确映射
   docker port mediacrawler-api
   
   # 检查VNC服务日志
   docker-compose logs mediacrawler-api | grep vnc
   ```

2. **VNC密码错误**
   ```bash
   # 检查环境变量设置
   docker-compose exec mediacrawler-api env | grep VNC
   ```

### API服务问题
1. **API无法访问**
   ```bash
   # 检查API服务状态
   curl http://localhost:8100/health
   
   # 查看API日志
   docker-compose logs mediacrawler-api | grep api
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库配置
   docker-compose exec mediacrawler-api env | grep DB
   ```

### 浏览器相关问题
1. **浏览器无法启动**
   ```bash
   # 检查DISPLAY环境变量
   docker-compose exec mediacrawler-api env | grep DISPLAY
   
   # 检查X11服务
   docker-compose logs mediacrawler-api | grep xvfb
   ```

2. **浏览器崩溃**
   - 增加共享内存大小：在docker-compose.yml中调整`shm_size`
   - 检查系统资源使用情况

## 性能优化

### 资源配置
```yaml
services:
  mediacrawler-api:
    deploy:
      resources:
        limits:
          cpus: '2.0'        # CPU限制
          memory: 4G         # 内存限制
        reservations:
          cpus: '1.0'        # CPU预留
          memory: 2G         # 内存预留
```

### 存储优化
```yaml
volumes:
  - ./data:/app/data
  - ./logs:/app/logs
  # 使用命名卷提高IO性能
  - app_cache:/app/.cache
```

## 安全建议

1. **修改默认密码**
   ```yaml
   environment:
     - VNC_PASSWORD=your_secure_password
   ```

2. **限制网络访问**
   ```yaml
   networks:
     - internal
   ```

3. **使用HTTPS**（生产环境）
   - 配置反向代理（如Nginx）
   - 添加SSL证书

## 扩展配置

### 添加Redis缓存
取消docker-compose.yml中Redis服务的注释：
```yaml
redis:
  image: redis:7-alpine
  container_name: mediacrawler-redis
  ports:
    - "6379:6379"
  restart: unless-stopped
```

### 添加MySQL数据库
取消docker-compose.yml中MySQL服务的注释：
```yaml
mysql:
  image: mysql:8.0
  container_name: mediacrawler-mysql
  environment:
    MYSQL_ROOT_PASSWORD: root123
    MYSQL_DATABASE: mediacrawler
  ports:
    - "3306:3306"
  restart: unless-stopped
```

## 更新升级

### 更新代码
```bash
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

### 数据备份
```bash
# 备份数据目录
tar -czf backup_$(date +%Y%m%d).tar.gz data/

# 备份数据库（如果使用容器数据库）
docker-compose exec mysql mysqldump -u root -p mediacrawler > backup.sql
```

## 监控和日志

### 日志查看
```bash
# 实时查看所有日志
docker-compose logs -f

# 查看特定时间段的日志
docker-compose logs --since="2h" mediacrawler-api
```

### 健康检查
容器内置健康检查，可以通过以下方式查看：
```bash
docker-compose ps
# 查看Health状态列
```

### 监控指标
```bash
# 查看容器资源使用情况
docker stats mediacrawler-api
``` 