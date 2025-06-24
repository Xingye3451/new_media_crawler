# 使用 Ubuntu 20.04 以上的系统作为基础镜像
FROM ubuntu:20.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# 更新软件包列表并安装 Python 3.10 和 pip
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.9 python3.9-venv python3-pip ffmpeg libsm6 libxext6 vim

# 设置工作目录
WORKDIR /app

# 将本地文件复制到镜像中的 /app 文件夹下
COPY . /app

# 创建虚拟环境
RUN python3.9 -m venv .venv

# 激活虚拟环境
ENV PATH="/app/.venv/bin:$PATH"

# 安装项目依赖
RUN pip install -r requirements.txt

# 安装 Playwright 浏览器驱动
RUN playwright install
RUN playwright install-deps

# 设置容器启动时执行的命令，这里使用 tail -f 保持容器运行
CMD tail -f /dev/null