# 使用指定的Python 3.10基础镜像
FROM docker.m.daocloud.io/library/python:3.10

# 设置工作目录
WORKDIR /app

# 复制项目文件到容器中
COPY . .

# 安装依赖
RUN pip install --no-cache-dir --default-timeout=100 --retries=5 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 暴露3000端口
EXPOSE 3000

# 设置环境变量
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# 启动命令
CMD ["python", "app.py"]