# 远程桌面配置说明

## 概述
MediaCrawler 现在支持通过配置文件管理远程桌面(VNC)设置，不再需要硬编码地址。

## 配置文件位置
- 开发环境: `config/config_dev.yaml`
- 生产环境: `config/config_prod.yaml`  
- 本地环境: `config/config_local.yaml`

## 配置参数说明

### remote_desktop 配置块
```yaml
remote_desktop:
  # 是否启用远程桌面功能
  enabled: true
  
  # VNC Web界面完整URL
  vnc_url: "http://192.168.31.231:6080/vnc.html"
  
  # VNC服务器主机地址
  vnc_host: "192.168.31.231"
  
  # VNC服务器端口
  vnc_port: 6080
  
  # VNC密码（可选）
  vnc_password: ""
  
  # 显示器编号（通常为1）
  display_number: 1
  
  # 连接超时时间（秒）
  connection_timeout: 5
  
  # 最大等待时间（秒，登录超时）
  max_wait_time: 1800
  
  # 状态检查间隔（秒）
  check_interval: 3
```

## 环境变量配置
生产环境可以通过环境变量动态设置：

```bash
# 设置VNC相关环境变量
export VNC_URL="http://your-vnc-server:6080/vnc.html"
export VNC_HOST="your-vnc-server"
export VNC_PORT="6080"
export VNC_PASSWORD="your-password"
export DISPLAY_NUMBER="1"
export REMOTE_DESKTOP_ENABLED="true"
```

## 配置示例

### 开发环境配置
```yaml
remote_desktop:
  enabled: true
  vnc_url: "http://192.168.31.231:6080/vnc.html"
  vnc_host: "192.168.31.231"
  vnc_port: 6080
  vnc_password: ""
  display_number: 1
  connection_timeout: 5
  max_wait_time: 1800
  check_interval: 3
```

### 生产环境配置
```yaml
remote_desktop:
  enabled: true
  vnc_url: "${VNC_URL:-http://localhost:6080/vnc.html}"
  vnc_host: "${VNC_HOST:-localhost}"
  vnc_port: ${VNC_PORT:-6080}
  vnc_password: "${VNC_PASSWORD:-}"
  display_number: ${DISPLAY_NUMBER:-1}
  connection_timeout: 5
  max_wait_time: 1800
  check_interval: 3
```

## 使用方法

### 1. 修改配置文件
根据你的环境修改对应的配置文件中的 `remote_desktop` 配置块。

### 2. 重启应用
修改配置后需要重启MediaCrawler应用以使配置生效。

### 3. 测试连接
启动远程桌面登录功能时，系统会自动检查VNC服务是否可用。

## 故障排除

### 常见问题
1. **无法连接到远程桌面**
   - 检查VNC服务器是否运行
   - 确认防火墙设置允许访问VNC端口
   - 验证配置文件中的地址和端口是否正确

2. **远程桌面功能被禁用**
   - 检查配置文件中 `enabled` 是否设置为 `true`
   - 确认环境变量 `REMOTE_DESKTOP_ENABLED` 设置正确

3. **登录超时**
   - 调整 `max_wait_time` 参数
   - 减少 `check_interval` 提高检查频率

## 注意事项
- 修改配置文件后需要重启应用
- 确保VNC服务器安全配置，避免未经授权的访问
- 生产环境建议使用环境变量而不是硬编码敏感信息
- 定期检查VNC服务器的可用性和性能

## 技术架构
- 配置管理：使用 `config/config_manager.py` 统一管理
- 前端获取：通过 `/login/status/{session_id}` API 获取VNC地址
- 后端处理：自动从配置文件读取VNC设置
- 环境适配：支持开发、测试、生产环境的不同配置 