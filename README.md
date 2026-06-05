# 客服升级值班交接系统

本地客服升级工单管理与值班交接系统，基于 Flask + React + SQLite 构建，支持完整的工单创建、交接批次管理、角色切换、数据导出等功能。

## 技术栈

- **后端**: Python 3.12+ / Flask 3.0 / Flask-SQLAlchemy / SQLite
- **前端**: React 18 / TypeScript / Vite / Tailwind CSS / Zustand
- **API 风格**: RESTful JSON API

## 项目结构

```
├── backend/                    # Flask 后端
│   ├── app.py                  # 应用入口
│   ├── models.py               # 数据模型
│   ├── validators.py           # 数据验证
│   ├── routes/                 # API 路由
│   │   ├── auth.py             # 角色/认证
│   │   ├── tickets.py          # 升级单
│   │   ├── batches.py          # 交接批次
│   │   ├── history.py          # 状态历史
│   │   ├── export.py           # 数据导出
│   │   └── dashboard.py        # 看板统计
│   ├── services/               # 业务逻辑
│   │   ├── ticket_service.py   # 工单服务
│   │   ├── batch_service.py    # 批次服务
│   │   └── history_service.py  # 历史服务
│   ├── requirements.txt        # Python 依赖
│   └── data.db                 # SQLite 数据库（自动创建）
├── src/                        # React 前端
│   ├── pages/                  # 页面组件
│   ├── components/             # 公共组件
│   ├── services/               # API 服务
│   ├── store/                  # 状态管理
│   ├── types/                  # TypeScript 类型
│   └── utils/                  # 工具函数
├── dist/                       # 前端构建产物
├── run_backend.py              # 后端启动脚本
├── package.json                # 前端依赖
└── vite.config.ts              # Vite 配置
```

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
cd backend
python -m pip install -r requirements.txt
cd ..

# 安装前端依赖
npm install
```

### 2. 构建前端

```bash
npm run build
```

### 3. 启动后端服务

```bash
python run_backend.py
```

服务将在 `http://localhost:5000` 启动，同时提供静态页面和 API 接口。

### 4. 访问系统

打开浏览器访问 `http://localhost:5000`

## 演示账号

系统预设 3 个演示账号，可在页面右上角切换：

| 用户名 | 角色 | 说明 |
|--------|------|------|
| `cs_demo` | 普通客服 | 创建升级单、查看、导出 |
| `handover_demo` | 交班人 | 创建交接批次 |
| `receiver_demo` | 接班人 | 确认/退回交接 |

## 核心功能演示

### 主流程示例

1. **创建升级单**（使用 `cs_demo` 普通客服）
   - 点击「升级单」→「新建升级单」
   - 填写：
     - 客户名称：测试客户001
     - 严重级别：高危
     - 责任人：张三
     - 截止时间：选择未来3天
     - 进展：客户反馈系统登录异常
   - 提交，查看新工单在列表中显示

2. **创建交接批次**（切换到 `handover_demo` 交班人）
   - 点击「交接批次」→「新建交接批次」
   - 批次名称：2026-06-05 白班交接
   - 描述：白班未结事项
   - 勾选刚才创建的工单和示例工单
   - 提交，批次状态为「待确认」

3. **确认交接**（切换到 `receiver_demo` 接班人）
   - 点击「交接批次」，点击刚才创建的批次
   - 查看批次详情，确认工单列表
   - 点击「确认交接」，状态变为「已确认」
   - 查看操作日志，确认历史记录已写入

### 失败路径演示

#### 失败路径 1：普通客服关闭逾期高危单

```bash
# 使用 curl 测试
curl -X POST http://localhost:5000/api/tickets/2/close \
  -H "Content-Type: application/json" \
  -b "session=cs_session"

# 预期返回：
# {"success":false,"error":"权限不足：普通客服不能关闭逾期的高危升级单，请联系主管处理"}
```

页面操作：
1. 保持 `cs_demo` 普通客服角色
2. 打开 ID 为 2 的升级单（示例客户B，严重级别 critical，已逾期）
3. 点击「关闭工单」
4. 系统弹出错误提示：权限不足

#### 失败路径 2：同一未结单进入两个开放交接

```bash
# 先创建第一个批次包含工单 1
curl -X POST http://localhost:5000/api/batches \
  -H "Content-Type: application/json" \
  -d '{"name":"批次A","ticket_ids":[1],"handover_person":"交班老李"}'

# 再尝试创建第二个批次也包含工单 1
curl -X POST http://localhost:5000/api/batches \
  -H "Content-Type: application/json" \
  -d '{"name":"批次B","ticket_ids":[1],"handover_person":"交班老李"}'

# 预期返回：
# {"success":false,"error":"工单 1 已在另一个待确认的交接批次中"}
```

页面操作：
1. 使用 `handover_demo` 创建第一个批次，勾选工单 1
2. 再次创建第二个批次，尝试勾选工单 1
3. 系统不允许勾选（工单已在其他待确认批次中灰显）

#### 失败路径 3：重复确认同一批次

```bash
# 确认批次 1 第一次
curl -X POST http://localhost:5000/api/batches/1/confirm \
  -H "Content-Type: application/json" \
  -d '{"receiver_person":"接班小张"}'

# 再次确认同一个批次
curl -X POST http://localhost:5000/api/batches/1/confirm \
  -H "Content-Type: application/json" \
  -d '{"receiver_person":"接班小张"}'

# 预期返回：
# {"success":false,"error":"该交接批次已经确认过，不能重复确认"}
```

页面操作：
1. 使用 `receiver_demo` 确认一个批次
2. 刷新页面再次进入同一批次详情
3. 「确认交接」按钮已灰显，点击弹出错误提示
4. 查看操作日志，确认历史记录只有一条

### 数据一致性验证

1. **重启前记录数据**
   - 访问看板，记录各统计数值
   - 记录工单列表数量
   - 导出 tickets.csv 备用

2. **重启服务**
   ```bash
   # Ctrl+C 停止服务，重新启动
   python run_backend.py
   ```

3. **重启后验证**
   - 看板数量与重启前完全一致
   - 工单详情、状态、进展信息完整保留
   - 操作日志完整可追溯
   - 再次导出 CSV，内容与之前一致

### 数据导出

- CSV 导出：`GET /api/export/tickets?format=csv`
- JSON 导出：`GET /api/export/tickets?format=json`
- 支持按状态和严重级别过滤：`GET /api/export/tickets?format=csv&severity=critical&status=overdue`

## API 接口说明

### 升级单接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tickets` | 获取升级单列表（支持 status/severity/assignee 过滤） |
| GET | `/api/tickets/:id` | 获取单个升级单详情 |
| POST | `/api/tickets` | 创建升级单 |
| PUT | `/api/tickets/:id` | 更新升级单 |
| POST | `/api/tickets/:id/close` | 关闭升级单 |

### 交接批次接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/batches` | 获取批次列表 |
| GET | `/api/batches/:id` | 获取批次详情（含工单列表） |
| POST | `/api/batches` | 创建交接批次 |
| POST | `/api/batches/:id/confirm` | 确认交接 |
| POST | `/api/batches/:id/return` | 退回交接 |

### 其他接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/stats` | 获取看板统计数据 |
| GET | `/api/history` | 获取状态历史 |
| GET | `/api/current-role` | 获取当前角色 |
| POST | `/api/switch-role` | 切换角色 |
| GET | `/api/export/tickets` | 导出台工单数据 |
| GET | `/api/export/batches` | 导出批次数据 |

## 开发模式

如需同时运行前端开发服务器（热更新）：

```bash
# 终端 1：启动后端
python run_backend.py

# 终端 2：启动前端开发服务器
npm run dev
```

访问 `http://localhost:5173`，API 请求会自动代理到后端。

## 数据库说明

- SQLite 数据库文件：`backend/data.db`
- 首次启动自动创建表结构和示例数据
- 如需重置数据，删除 `backend/data.db` 后重启服务即可

## 权限控制

| 操作 | 普通客服 | 交班人 | 接班人 |
|------|----------|--------|--------|
| 查看升级单 | ✅ | ✅ | ✅ |
| 创建升级单 | ✅ | ❌ | ❌ |
| 编辑进展 | ✅ | ❌ | ✅ |
| 创建交接批次 | ❌ | ✅ | ❌ |
| 确认/退回交接 | ❌ | ❌ | ✅ |
| 导出数据 | ✅ | ✅ | ✅ |

> **特殊限制**：普通客服不能关闭逾期的高危升级单，此限制在服务层逻辑中校验，不是简单的权限控制。

## 测试

### 后端权限回归测试

**重要**：运行测试前必须先关闭后端服务，否则数据库文件会被占用导致测试无法运行。

```bash
# ========== 权限回归测试（推荐先跑这个） ==========
# 1. 先关闭正在运行的后端服务（Ctrl+C）
# 2. 运行权限漏洞回归测试
python test_batch_permission.py
```

**预期输出（全部通过）：**
```
[INFO] 正在清理测试环境...
[INFO] 已删除旧数据库文件
============================================================
交接批次权限漏洞回归测试
============================================================
[INFO] 数据库初始化完成
...
测试结果: 19 通过, 0 失败
============================================================

[INFO] 所有测试全部通过！权限漏洞已修复！
```

**常见错误处理：**

| 现象 | 退出码 | 原因 | 解决方法 |
|------|--------|------|----------|
| 数据库文件被占用错误 | 2 | 后端服务仍在运行 | 先关闭 `run_backend.py` 进程 |
| 数据库初始化失败 | 3 | 数据库文件被其他进程锁定 | 检查并关闭占用 `backend/data.db` 的程序 |
| 测试执行异常 | 4 | 代码或数据问题 | 查看堆栈跟踪排查具体错误 |

```bash
# ========== 完整 API 集成测试 ==========
python test_api.py
```

**预期输出（全部通过）：**
```
[INFO] 正在清理测试环境...
[INFO] 已删除旧数据库文件
Testing API endpoints...
==================================================
...
测试结果: 15 通过, 0 失败
==================================================

[INFO] 所有测试全部通过！
```

### 退出码说明

| 退出码 | 含义 |
|--------|------|
| 0 | 所有测试通过 |
| 1 | 有测试断言失败 |
| 2 | 数据库文件被占用，无法清理 |
| 3 | 数据库初始化失败 |
| 4 | 测试执行过程中发生异常 |
| 130 | 用户中断 (Ctrl+C) |
| 99 | 其他未知错误 |

### 权限测试覆盖场景

| 测试场景 | 预期结果 |
|---------|---------|
| 普通客服 (cs) 确认批次 | 返回 403，状态不变，不写历史 |
| 交班人 (handover) 确认批次 | 返回 403，状态不变，不写历史 |
| 接班人 (receiver) 确认批次 | 返回 200，状态 confirmed，写历史 |
| 重复确认同一批次 | 返回 400，不重复写历史 |
| 普通客服退回批次 | 返回 403，状态不变 |
| 交班人退回批次 | 返回 403，状态不变 |
| 接班人退回批次 | 返回 200，状态 returned，写历史 |

### 权限控制说明

**根因修复**：在服务层 `backend/services/batch_service.py` 的 `confirm_batch()` 和 `return_batch()` 函数入口处添加角色校验，确保只有 `receiver` 角色可以执行确认/退回操作。校验在任何数据库修改之前执行，无权限时立即返回 403 错误，不修改批次状态、接班人、确认时间，也不新增历史记录。

**API 层**：`backend/routes/batches.py` 通过 `get_current_role()` 获取当前会话角色（登录或切换后的角色），传递给服务层进行校验。

**前端**：`src/pages/BatchDetail.tsx` 和 `src/pages/BatchList.tsx` 通过 `hasPermission()` 检查权限，隐藏无权限的操作按钮，形成深度防御。

## 类型检查

```bash
# 前端 TypeScript 检查
npm run check

# 构建生产版本
npm run build
```
