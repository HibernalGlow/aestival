# AestivalFlow - Tauri + SvelteKit + Python

Python工具链可视化编排与执行平台，基于 Tauri (Rust) + SvelteKit (TypeScript) + Python FastAPI 构建。

## 🌟 特性

- **跨平台桌面应用** - 基于 Tauri 构建
- **现代化 Web UI** - SvelteKit + TypeScript + Tailwind CSS
- **Python 后端** - FastAPI 提供 REST API 服务
- **轻量级架构** - 不使用 PyInstaller 打包，直接调用系统 Python
- **热重载** - 开发时前后端都支持热重载
- **可视化编排** - 支持工具节点拖拽编排

## 🏗️ 架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   SvelteKit     │◄──►│      Tauri       │◄──►│  Python Package │
│   Frontend      │    │   (Rust Core)    │    │  (系统安装)      │
│                 │    │                  │    │                 │
│ • TypeScript    │    │ • Window Mgmt    │    │ • aestival-     │
│ • Tailwind CSS  │    │ • Shell Plugin   │    │   backend       │
│ • Component UI  │    │ • Process Mgmt   │    │ • FastAPI       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📋 环境要求

- **Node.js** (v18+) - [下载](https://nodejs.org/)
- **Yarn** - `npm install -g yarn`
- **Python 3.11+** - [下载](https://python.org/)
- **Rust** - [安装](https://rustup.rs/)

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装前端依赖和 Python 后端包
yarn install-reqs
```

这会执行：
- `yarn install` - 安装 Node.js 依赖
- `pip install -e ./src-python` - 以开发模式安装 Python 后端包

### 2. 安装工具包（可选）

如果需要使用工具适配器功能：

```bash
# 完整安装（包含所有工具包）
pip install aestival-backend[tools]

# 或单独安装需要的工具
pip install repacku trename rawfilter crashu
```

> **注意**: 如果你已经有本地开发版本的工具包（通过 `pip install -e` 安装），
> 基础安装不会覆盖它们。只有 `[tools]` 选项会从 GitHub 安装工具包。

### 3. 开发模式

```bash
# 完整 Tauri 开发环境（推荐）
yarn tauri:dev

# 或分开运行
yarn dev          # 前端开发服务器
yarn dev:python   # Python 后端（热重载）
```

### 4. 生产构建

```bash
yarn tauri:build
```

## 📁 项目结构

```
AestivalFlow/
├── src/                    # SvelteKit 前端
│   ├── lib/               # 组件和工具
│   └── routes/            # 页面路由
├── src-python/            # Python 后端
│   ├── aestival_backend/  # 包入口点
│   ├── adapters/          # 工具适配器
│   ├── api/               # API 端点
│   └── pyproject.toml     # Python 包配置
├── src-tauri/             # Tauri 应用
│   ├── src/               # Rust 源码
│   └── tauri.conf.json    # Tauri 配置
└── package.json           # Node.js 配置
```

## ⚙️ 配置

### Python 后端配置

创建 `config/python.json`：

```json
{
  "python_path": "python",
  "port": 8009,
  "host": "127.0.0.1",
  "auto_restart": true,
  "startup_timeout_ms": 10000,
  "dev_mode": false
}
```

### 工具适配器

工具包作为可选依赖，避免覆盖本地开发版本：

```toml
# pyproject.toml
[project.optional-dependencies]
tools = [
    "autorepack @ git+https://github.com/HibernalGlow/AutoRepack.git",
    "trename @ git+https://github.com/HibernalGlow/trename.git",
    # ...
]
```

## 🔧 开发命令

| 命令 | 说明 |
|------|------|
| `yarn dev` | 启动前端开发服务器 |
| `yarn dev:python` | 启动 Python 后端（热重载） |
| `yarn dev:standalone` | 同时启动前后端 |
| `yarn tauri:dev` | 完整 Tauri 开发环境 |
| `yarn tauri:build` | 生产构建 |
| `yarn check` | TypeScript 类型检查 |

## 📚 相关资源

- [Tauri 文档](https://tauri.app/start/)
- [SvelteKit 文档](https://kit.svelte.dev/docs)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

## 📄 许可证

MIT License
