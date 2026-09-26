# GXU 校园文件智能助手

基于广西大学文件系统（`wjxt.gxu.edu.cn`）的智能问答系统。学生用自然语言提问，系统检索官方文件并生成带引用的回答。

## ✨ 功能总览

### 智能问答
- **自然语言提问**：直接问"保研需要什么条件？""国家奖学金多少钱？"，无需搜索文件
- **带引用回答**：每个回答标注来源文件（标题、部门、日期），可核验
- **流式输出**：回答实时逐字显示，不用等
- **智能路由**：
  - 简单问题 → 快速检索直接回答（秒级）
  - 复杂问题（对比类、多跳推理，如"保研和国奖哪个要求高"）→ Agent 自主多步搜索后综合回答
- **同义词扩展**：自动识别口语说法（"保研"→"推免"、"绩点"→"加权平均成绩"），弥补日常用语和官方术语的鸿沟
- **引用来源可折叠**：点击"参考来源"展开/收起详情

### 文档管理（管理页）
- **文档列表**：查看所有已入库文件（标题、部门、日期、分块数、状态）
- **统计面板**：文档总数、已索引数、向量块数、错误数
- **刷新**：随时查看最新状态

### 数据处理
- **自动过滤**：摄入时剔除临时通知（停电/施工/名单/处分决定/比赛通知等），只保留长期有效的规章制度与政策
- **版本去重**：同一政策保留最新版，自动删除旧版（如历年的保研实施办法只留最新）
- **增量同步**：`sync.bat` 一键同步新文件，几秒完成；可配 Windows 计划任务每周自动执行
- **内容变更感知**：政策修订后重新摄入会自动重建索引，无需手动处理

### 对话历史
- 会话保存：刷新页面后历史消息仍可查看（后端 SQLite 持久化）

## 🚀 快速上手（同学视角）

1. 启动系统（见下方"快速启动"）
2. 浏览器打开 **http://localhost:5173**
3. 直接提问，例如：
   - "保研需要什么条件？GPA要求多少？"
   - "国家奖学金多少钱？怎么申请？"
   - "转专业有什么要求？"
   - "考试作弊会怎么处理？"
   - "宿舍能用大功率电器吗？"
4. 左侧"文档管理"可查看系统里有哪些文件

## 系统架构

```
前端 (React + Vite)  ──►  nginx /api 代理  ──►  后端 (FastAPI)
                                                  │
                              ┌───────────────────┼───────────────────┐
                              ▼                   ▼                   ▼
                        向量检索 (ChromaDB)    LLM (DeepSeek)     SQLite (元数据)
```

- **后端**: FastAPI + ChromaDB 向量检索 + BGE 中文嵌入 + DeepSeek 生成
- **前端**: React + Vite，聊天界面 + 文档管理
- **摄入**: `gxu-wjxt` SDK 爬取文件系统 → 过滤 → 分块 → 向量化入库

## 快速启动

### 1. 启动后端

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

首次启动会自动加载嵌入模型（约 1 分钟）。

### 2. 启动前端

```bash
cd frontend
npm run dev
```

打开浏览器访问 **http://localhost:5173**

## 项目结构

```
FileSystemAgent/
├── backend/                     # Python 后端 (FastAPI)
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── core/config.py       # 配置（从 .env 读取）
│   │   ├── models/              # SQLAlchemy 模型 + Pydantic DTO
│   │   ├── db/session.py        # SQLite 异步连接
│   │   ├── services/
│   │   │   ├── crawler.py       # (预留) 爬虫封装
│   │   │   ├── parser.py        # HTML → 纯文本
│   │   │   ├── chunker.py       # 中文感知分块
│   │   │   ├── embedder.py      # BGE 嵌入模型
│   │   │   ├── vector_store.py  # ChromaDB 向量存储
│   │   │   ├── llm_service.py   # DeepSeek 生成 + SSE 流式
│   │   │   ├── query_engine.py  # 查询引擎（同义词扩展 + 路由）
│   │   │   ├── agent.py         # Agent 复杂查询（多步搜索）
│   │   │   └── pipeline.py      # 摄入管道
│   │   └── api/routes/
│   │       ├── chat.py          # /api/chat（SSE 流式）
│   │       └── admin.py         # 文档管理 API
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env                     # LLM API Key 等配置
│
├── frontend/                    # React + Vite 前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat/            # 聊天界面
│   │   │   └── Admin/           # 文档管理
│   │   ├── services/api.ts      # 后端 API 调用（SSE）
│   │   └── types/               # TypeScript 类型
│   ├── Dockerfile
│   ├── nginx.conf
│   └── vite.config.ts
│
├── scripts/                     # 数据摄入脚本
│   ├── ingest.ts                # 全量导入
│   ├── sync.ts                  # 增量同步
│   ├── cleanup_docs.py          # 文档清理（过滤+去重）
│   ├── fix_consistency.py       # 数据一致性修复
│   ├── seed_test_data.py        # 测试数据
│   └── test_qa.py               # 问答质量测试
│
├── sync.bat                     # 一键增量同步
├── docker-compose.yml           # Docker 编排（待启用）
└── README.md
```

## 数据摄入

### 全量导入（首次使用）

```bash
cd scripts
WJXT_USERNAME=你的学号 WJXT_PASSWORD=你的密码 npx tsx ingest.ts
```

- 遍历整个文件系统（约 6000+ 文件，需 40 分钟左右）
- 自动过滤临时通知（停电/施工/名单/处分决定等），只保留长期有效政策
- 政策文件保留最新版本，自动去重旧版

### 增量同步（日常维护）⭐

```bash
sync.bat        # 一键运行（可配计划任务自动执行）
```

或手动：

```bash
cd scripts
WJXT_USERNAME=你的学号 WJXT_PASSWORD=你的密码 npx tsx sync.ts
```

- 只处理上次同步之后的文件（**几秒钟完成**）
- 内容变更的政策自动重建索引
- 新文件自动过滤临时通知

**原理**：`data/last_sync.json` 记录上次同步时间，文件系统按时间倒序，遇到旧文件即停止。

## 数据快照（跨机器分发数据）⭐

跑一次全量摄入要 40 分钟 + embedding 时间。**快照功能**把爬好的数据打包发布到
GitHub Release，其他环境直接下载即用，**不用重新爬取和向量化**。

### 典型场景

| 场景 | 操作 |
|------|------|
| 本地已有数据，想分享给学长/服务器 | `snapshot.bat publish` |
| 新环境要开发，不想爬 40 分钟 | `snapshot.bat import` |
| 服务器首次部署 | `./snapshot.sh import` |

### 命令

```bash
python scripts/snapshot.py info      # 查看当前数据状态
python scripts/snapshot.py export    # 导出快照到 snapshots/
python scripts/snapshot.py publish   # 导出并发布到 GitHub Release
python scripts/snapshot.py import    # 下载并恢复最新快照
python scripts/snapshot.py list      # 列出所有已发布快照
```

Windows 用 `snapshot.bat <命令>`，Linux/macOS 用 `./snapshot.sh <命令>`。

### 说明

- 快照内容：SQLite 元数据 + ChromaDB 向量库 + manifest（版本/文档数）
- 快照大小：约 **77 MB**（2990 文档 / 8339 向量块）
- 导入会自动备份旧数据到 `snapshots/backup-*/`
- ⚠️ **导出前请停止后端**，避免 ChromaDB 写入不一致（脚本会检测并提示）
- 发布/下载需访问 GitHub，国内网络需代理（见下方"网络代理"）

## 自动同步（Windows 计划任务）

让系统每周自动同步新文件：

1. 创建 `sync.conf`（复制 `sync.conf.example` 并填写账号密码）：
   ```
   WJXT_USERNAME=你的学号
   WJXT_PASSWORD=你的密码
   ```
2. 打开"任务计划程序" → 创建基本任务
3. 触发器：每周（如每周一 8:00）
4. 操作：启动程序 → 程序选 `sync.bat`（位于项目根目录）
5. 完成。之后每周自动同步，无需人工干预。

> ⚠️ 计划任务运行 sync.bat 时会自动启动后端（若未运行）。请确保电脑在计划时间开机。

## 环境配置

在 `backend/.env` 配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | DeepSeek API Key | 必填 |
| `LLM_MODEL` | 大模型 | `deepseek-chat` |
| `EMBEDDING_MODEL` | 嵌入模型 | `BAAI/bge-small-zh-v1.5` |

## 数据目录

- `backend/school_rag.db` — 文档元数据、对话历史
- `backend/chroma_data/` — 向量数据
- `data/last_sync.json` — 增量同步标记

## 网络代理

本项目访问 GitHub（发布/下载快照、推送代码）需要代理。

```bash
# git 全局代理（已配置过）
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890

# 快照命令临时走代理
HTTPS_PROXY=http://127.0.0.1:7890 ./snapshot.sh publish
```

## 服务器部署（Linux）⭐

学校服务器能访问校园网（`wjxt.gxu.edu.cn`），既作**数据源头**也作**最终部署点**：

```
服务器 (Linux, 校园内网)                 GitHub Release         本地开发
  ├─ 定期 sync 爬新文件           ──►   快照 .tar.gz    ──►   ├─ snapshot import
  ├─ snapshot publish 发布快照                                └─ 开发调试
  └─ 跑 agent 服务（同学访问）
```

### 首次部署

```bash
git clone https://github.com/qingqing-me/FileSystemAgent.git
cd FileSystemAgent

# 1. 后端依赖
cd backend && pip install -r requirements.txt && cd ..

# 2. 配置 API Key
cp backend/.env.example backend/.env
vim backend/.env          # 填入 LLM_API_KEY

# 3. 导入数据（无需爬取，直接从 Release 下载）
./snapshot.sh import

# 4. 启动后端
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 前端（生产构建 + nginx）

```bash
cd frontend
npm install
npm run build             # 产物在 dist/

# nginx 托管 dist/ 并代理 /api 到 :8000（配置见 frontend/nginx.conf）
cp frontend/nginx.conf /etc/nginx/conf.d/gxu-agent.conf
systemctl reload nginx
```

### 定期更新数据（cron）

服务器在校园内网，可自动同步新文件并发布快照：

```bash
crontab -e

# 每周一 8:00：同步新文件 + 发布快照
0 8 * * 1 cd /opt/FileSystemAgent && WJXT_USERNAME=学号 WJXT_PASSWORD=密码 npx tsx scripts/sync.ts && HTTPS_PROXY=http://127.0.0.1:7890 ./snapshot.sh publish
```

这样服务器数据持续保持最新，本地开发随时 `snapshot import` 拉最新快照。

### Docker（可选）

Docker 部署文件已就绪（`Dockerfile`、`docker-compose.yml`、`nginx.conf`），需网络能访问 Docker Hub：

```bash
docker compose up -d --build
```

访问 http://localhost:8080
