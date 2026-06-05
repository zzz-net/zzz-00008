# 客服升级值班交接系统

本地客服升级工单管理与值班交接系统，基于 Flask + React + SQLite 构建，支持完整的工单创建、交接批次管理、角色切换、数据导出等功能。

## 技术栈

- **后端**: Python 3.12+ / Flask 3.0 / Flask-SQLAlchemy / SQLite
- **前端**: React 18 / TypeScript / Vite / Tailwind CSS / Zustand
- **API 风格**: RESTful JSON API

## 新增：值班排班与交接窗口联动

### 功能概述

班次排班模块让交接批次能够与值班计划真正联动：
- 班次包含：名称、值班人、起止时间、可接收严重级别、启停状态
- 批次创建时可选关联当前生效班次，接班人只能从该班次带出
- 越权角色（普通客服、交班人）不能创建/编辑/停用排班，只有 `receiver`（接班人角色）有 `manage_shifts` 权限
- 支持 CSV 批量导入/导出排班，导入会做字段、重复、时间格式校验，部分失败自动回滚，所有操作写入历史日志

### 冲突处理规则

| 冲突类型 | 处理方式 |
|----------|----------|
| 同一值班人时间重叠（激活班次） | 拒绝新建/编辑，返回 409，明确提示冲突的班次 |
| 停用班次被未完成（pending/confirmed）交接批次引用 | 拒绝停用，返回 409，列出引用的批次 |
| 跨天班次按日期查询 | 自动匹配起止时间跨当日的班次（含完全覆盖、当日开始、当日结束三种情况） |
| 确认交接时接班人 ≠ 班次值班人 | 拒绝确认，返回 400，提示必须由指定值班人确认 |

## 新增：值班提醒模块

### 功能概述

值班提醒模块让管理员（接班人）可以给特定班次或日期发布班前提醒，值班人登录后在首页和批次详情页看到待确认提醒：

- 管理员可发布提醒：标题、内容、关联班次、生效时间段、启停状态
- 值班人在首页看到「待确认提醒」区块，在交接批次详情页看到关联班次的提醒
- 同一班次同一时间段不能重复发布相同标题
- 过期或已停用的提醒不能再被确认
- 确认时自动记录当前用户和确认时间
- 支持 CSV 批量导入导出，导入时校验时间格式、重复数据和无效班次
- 所有操作（创建、编辑、停用、导入、确认）写入历史日志

### 权限控制

| 操作 | 普通客服 (cs) | 交班人 (handover) | 接班人 (receiver) |
|------|----------------|-------------------|-------------------|
| 查看提醒 | ✅（仅自己相关） | ✅（仅自己相关） | ✅（全部） |
| 确认提醒 | ✅ | ✅ | ✅ |
| 新建提醒 | ❌ | ❌ | ✅ |
| 编辑提醒 | ❌ | ❌ | ✅ |
| 停用提醒 | ❌ | ❌ | ✅ |
| 导入/导出 CSV | ❌ | ❌ | ✅ |

### 冲突与校验规则

| 规则 | 处理方式 |
|------|----------|
| 同班次同时间段同标题重复 | 返回 409 冲突 |
| 过期或停用提醒被确认 | 返回 400 拒绝 |
| 同一用户重复确认同一提醒 | 返回 400 拒绝 |
| CSV 时间格式错误 | 返回 400 + 逐行错误说明 |
| CSV 引用不存在的班次 | 返回 400 + 逐行错误说明 |
| CSV 缺必填列 | 返回 400 + 缺失列名 |

### 提醒 API 接口

| 方法 | 路径 | 说明 | 所需权限 |
|------|------|------|----------|
| GET | `/api/reminders` | 获取提醒列表（支持 `date`, `shift_id`, `is_active` 筛选） | `view_reminders` |
| GET | `/api/reminders/my-pending` | 当前用户待确认的提醒 | `confirm_reminders` |
| GET | `/api/reminders/for-shift/:shift_id` | 指定班次的提醒 | `view_reminders` |
| GET | `/api/reminders/:id` | 获取提醒详情 | `view_reminders` |
| POST | `/api/reminders` | 创建提醒 | `manage_reminders` |
| PUT | `/api/reminders/:id` | 编辑提醒 | `manage_reminders` |
| POST | `/api/reminders/:id/disable` | 停用提醒 | `manage_reminders` |
| POST | `/api/reminders/:id/confirm` | 确认提醒 | `confirm_reminders` |
| GET | `/api/reminders/export` | CSV 导出（支持 `?format=json` 导出 JSON） | `manage_reminders` |
| POST | `/api/reminders/import` | CSV 批量导入 | `manage_reminders` |

#### 创建/编辑提醒请求体

```json
{
  "title": "班前安全检查",
  "content": "请登录系统前检查网络连通性...",
  "shift_id": 1,
  "effective_start": "2026-06-05T09:00:00",
  "effective_end": "2026-06-05T18:00:00",
  "is_active": true
}
```

#### 成功响应示例

```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "班前安全检查",
    "content": "...",
    "is_active": true,
    "confirmations": [
      {"confirmed_by": "接班小张", "confirmed_at": "2026-06-05T09:05:30"}
    ]
  }
}
```

#### CSV 导入响应示例（有校验失败）

```json
{
  "success": false,
  "error": "数据校验失败，未导入任何记录",
  "details": [
    "第 2 行：提醒标题不能为空",
    "第 2 行：生效开始时间格式错误，应为 YYYY-MM-DD HH:MM:SS",
    "第 3 行：无效班次名称「不存在的班次」"
  ]
}
```

### CSV 导入/导出字段

| 列名 | 必填 | 说明 | 示例 |
|------|------|------|------|
| 提醒标题 | ✅ | 提醒的标题（同班次同时间段不能重复） | 班前安全检查 |
| 提醒内容 | ✅ | 提醒的详细内容 | 请检查网络、系统登录状态 |
| 生效开始时间 | ✅ | 格式：`YYYY-MM-DD HH:MM:SS` | 2026-06-05 09:00:00 |
| 生效结束时间 | ✅ | 格式同上，且需晚于生效开始 | 2026-06-05 18:00:00 |
| 关联班次名称 | ❌ | 对应 `DutyShift.name`，留空则不关联 | 白班 |
| 是否启用 | ❌ | `是`/`否`（默认 `是`） | 是 |

> CSV 文件需为 UTF-8 编码（建议带 BOM，Excel 另存为 CSV UTF-8 即可）。

### 验收步骤

1. **管理员发布提醒**
   - 使用 `receiver_demo` 登录，进入「值班提醒」
   - 点击「新建提醒」，填写标题、内容、选择班次、设置生效时间（覆盖当前时间）
   - 提交后列表显示新提醒，状态为「启用中」
   - 查看历史日志，确认已写入「创建提醒」记录

2. **重复提醒被拒绝**
   - 尝试创建相同标题 + 相同班次 + 时间重叠的提醒
   - 系统返回 409 冲突提示

3. **值班人在首页确认提醒**
   - 切换到任意值班人角色（如 `handover_demo`），确保该角色在提醒关联班次中
   - 首页顶部显示「待确认的值班提醒」琥珀色区块
   - 点击「确认提醒」，提醒立即从列表消失
   - 切换回 `receiver_demo` 查看提醒详情，确认人已记录

4. **批次详情页查看关联提醒**
   - 创建或打开一个关联了带提醒班次的交接批次
   - 批次详情页下方显示「关联班次的值班提醒」区块
   - 可直接在该页面确认提醒

5. **过期/停用提醒无法确认**
   - 创建一个提醒，手动停用到
   - 切换值班人角色，该提醒不再显示待确认，且详情页确认按钮不可用
   - 创建一个生效时间为过去时间段的提醒，同样无法确认

6. **CSV 导入导出**
   - 管理员点击「导出CSV」，得到含上述字段的 CSV 文件
   - 修改 CSV，故意添加错误数据（时间格式错误、无效班次）
   - 点击「导入CSV」上传坏数据，界面显示逐行错误原因，0 条导入
   - 修正 CSV 后重新导入，显示成功导入 N 条，历史日志写入记录

7. **数据跨重启保留**
   - 创建几条提醒并确认若干
   - 停止后端服务再启动
   - 验证提醒数据、确认记录、历史日志全部保留

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
# ========== 值班排班模块回归测试（推荐先跑这个） ==========
# 覆盖：跨重启数据保留、时间重叠冲突、停用被引用冲突、权限拒绝、CSV导入导出一致性
python test_shift_audit.py

# ========== 撤销功能完整回归测试（推荐先跑这个） ==========
# 1. 先关闭正在运行的后端服务（Ctrl+C）
# 2. 运行撤销功能审计测试（覆盖权限、冲突、跨重启、导出筛选）
python test_revoke_audit.py

# ========== 撤销功能流程测试 ==========
python test_revoke_flow.py

# ========== 权限回归测试 ==========
python test_batch_permission.py

# ========== 完整 API 集成测试 ==========
python test_api.py
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
