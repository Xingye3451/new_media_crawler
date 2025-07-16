# 使用 Ubuntu 20.04 以上的系统作为基础镜像
FROM tlkid/mediacrawler:20240728

# 设置工作目录
WORKDIR /app

# 将本地文件复制到镜像中的 /app 文件夹下
COPY . /app

# 安装项目依赖
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 设置容器启动时执行的命令，这里使用 tail -f 保持容器运行
CMD tail -f /dev/null