FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（chromadb 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先拷贝依赖文件，利用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码
COPY . .

# 数据目录（通过 volume 挂载持久化）
RUN mkdir -p /app/data

# 环境变量由 docker-compose 提供
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
