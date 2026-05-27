# 饮食健康 App

AI 营养师，科学定制你的饮食方案。

## 功能

- **AI 饮食方案生成** — 根据个人目标（减脂/增肌/健康）自动生成 7 天或 3 天食谱
- **智能食材替换** — 不喜欢某样食材？AI 推荐替代方案
- **问卷分析** — 填写饮食习惯问卷，AI 生成个性化膳食建议
- **采购清单** — 按天/按餐生成购物清单，支持按食材合并
- **订单锁定** — 已确认订单在配送日前 2 天内锁定，防止配送延误
- **健康追踪** — 记录体重、卡路里摄入、饮食合规率、心情
- **月度报告** — 体重趋势、平均合规率、卡路里统计
- **后台管理** — 超市分配、配送任务生成、用户管理

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy (async) + SQLite |
| 前端 | Vanilla JS SPA |
| AI | Qwen / DeepSeek API |
| 认证 | JWT |

## 快速开始

```bash
# 1. 配置环境变量
cd backend
cp .env.example .env   # 编辑 .env 填入 API Key

# 2. 启动后端
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. 浏览器打开
# http://localhost:8000
```

## 项目结构

```
backend/
  app/
    main.py              # FastAPI 入口
    core/                 # 配置、数据库、安全
    models/               # ORM 模型
    schemas/__init__.py   # Pydantic 校验
    api/v1/               # API 路由
    services/             # AI 调用、营养计算
frontend/
  index.html              # 用户端 SPA
  admin.html              # 后台管理
```

## 使用说明

1. 浏览器打开后输入昵称，点击"开始使用"
2. 首次使用填写个人信息和目标 → 填写饮食问卷 → 生成方案
3. 已有方案的用户登录后直接进入"今日饮食"页面
4. 管理员访问 `/admin` 进入后台管理
