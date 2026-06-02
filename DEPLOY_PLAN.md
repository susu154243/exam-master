# 刻印部署与管理方案

## 一、核心目标

1. **不影响线上服务** — 每次代码更新不干扰 :32220 正常做题
2. **本地电脑实操验证** — 改完后在自己电脑浏览器打开验证所有功能
3. **确认后提交上线** — 验证通过才切换，失败可回滚

## 二、整体流程

```
日常开发流程（一次迭代）:

refactor 分支改代码 → git commit
       ↓
本地电脑: ssh -L 32222:127.0.0.1:32222 root@118.89.184.64
       ↓
服务器上: gunicorn -w 2 -b 127.0.0.1:32222 app:app
       ↓
本地浏览器: http://localhost:32222 完整做题验证
       ↓
验证通过 → 关掉预览进程
       ↓
make deploy (备份 → 切 main → merge → 重启)
```

## 三、关键设计

### 1. git 分支隔离

| 分支 | 用途 |
|---|---|
| `main` | **线上运行版本**，:32220 服务永远跑这个分支 |
| `refactor` | 重构开发分支，改代码、调试、验证都在这里 |

### 2. 本地预览（SSH 端口转发）

预览服务绑在 **127.0.0.1:32222**（不对外暴露），通过 SSH 隧道映射到你本地电脑。

**为什么不用安全组或 Nginx：**
- 不需要改腾讯云安全组规则
- 不需要改 Nginx 配置
- 预览服务只有你能访问，别人打不开
- 一条命令搞定

### 3. 数据库安全

- `database.db` 在服务器上只有一份，预览和线上共享同一个数据库
- 建议预览前先备份（`make backup`）
- 预览只读不改核心数据（验证功能，不写入正式数据）

### 4. 回滚机制

`make rollback` 一键恢复：
- 数据库恢复到备份时间点
- git 代码回到 main 分支老版本
- 重启服务

## 四、架构调整目标（重构后目录）

```
/keyin/
├── app.py                  # Flask 入口（精简）
├── admin.py                # 管理后台 BP（精简）
├── auth.py                 # 权限装饰器（不变）
├── Makefile                # 部署/管理命令
├── routes/                 # 路由层（新增）
│   ├── auth.py
│   ├── practice.py
│   ├── exam.py
│   ├── stats.py
│   └── interaction.py
├── services/               # 业务逻辑层（新增）
│   ├── review_service.py
│   ├── license_service.py
│   └── import_service.py
├── models/                 # 数据访问层（拆分 models.py）
│   ├── db.py
│   ├── user.py
│   ├── subject.py
│   ├── question.py
│   ├── review.py
│   ├── license.py
│   ├── notification.py
│   └── settings.py
├── utils/                  # 纯工具（新增）
│   ├── fsrs.py
│   ├── html_sanitizer.py
│   └── image_upload.py
├── lib/                    → 删除
├── models.py               → 删除
├── static/ / templates/
└── database.db
```

## 五、实施步骤

### Step 1：基础设施

```bash
cd /keyin
git checkout -b refactor                    # 建重构分支
mkdir -p routes services models utils       # 创建目录
touch routes/__init__.py services/__init__.py models/__init__.py
```

然后写 Makefile（见下方）。

### Step 2：合并数据库连接

将 `lib/db.py` 迁入 `models/db.py`，统一使用线程级连接缓存版本。

### Step 3：拆分 models/ 子模块

把 4145 行的 models.py 按职责拆成 7 个文件（user / subject / question / review / license / notification / settings），`models/__init__.py` 统一导出保持兼容。

### Step 4：创建 services/

提取业务逻辑：
- `build_review_items()` — 复习状态计算
- 注册授权流程
- apkg 导入

### Step 5：拆分 routes/

按模块拆分 60 个路由到 routes/ 下。

### Step 6：拆分 utils/

提取 FSRS 算法、HTML 净化、图片上传。

### Step 7：清理收尾

删除 models.py、lib/，验证所有 import 正确。

## 六、Makefile 完整内容

```makefile
BACKUP_DIR = /keyin/backups
TIMESTAMP = $(shell date +%Y%m%d_%H%M%S)

# 备份（数据库 + 当前代码）
backup:
	@mkdir -p $(BACKUP_DIR)
	@cp /keyin/database.db $(BACKUP_DIR)/database.db.$(TIMESTAMP)
	@cd /keyin && git bundle create $(BACKUP_DIR)/code.$(TIMESTAMP).bundle HEAD
	@echo "备份完成: $(TIMESTAMP)"

# 启动预览（:32222，仅 127.0.0.1 监听）
preview:
	@pkill -f "gunicorn.*:32222" 2>/dev/null || true
	@cd /keyin && gunicorn -w 2 -b 127.0.0.1:32222 app:app &
	@sleep 2
	@curl -s -o /dev/null http://127.0.0.1:32222/ && echo "预览已启动: http://127.0.0.1:32222" || echo "启动失败"

# 关闭预览
preview-stop:
	@pkill -f "gunicorn.*:32222" 2>/dev/null && echo "预览已关闭" || echo "预览未运行"

# 部署上线（备份 → 切 main → merge → 重启）
deploy: backup
	@cd /keyin && git checkout main && git merge refactor && systemctl restart keyin
	@sleep 2
	@curl -s -o /dev/null http://127.0.0.1:32220/ && echo "部署完成" || echo "部署可能失败，请检查"

# 回滚
rollback:
	@echo "回滚到: $(TIMESTAMP)"
	@cp $(BACKUP_DIR)/database.db.$(TIMESTAMP) /keyin/database.db
	@cd /keyin && git checkout main && systemctl restart keyin
	@echo "回滚完成"
```

## 七、日常操作指南

### 开始一次重构迭代

```bash
# 在服务器上
cd /keyin
git checkout refactor
# ... 修改代码 ...
git add .
git commit -m "描述改动"
```

### 本地预览验证

```bash
# 在本地电脑终端（Windows 用 CMD/PowerShell，Mac 用终端）
ssh -L 32222:127.0.0.1:32222 root@118.89.184.64
# 保持这个窗口开着

# 在服务器另一个终端
cd /keyin
make preview               # 启动预览

# 然后在本地浏览器打开
# http://localhost:32222
# 验证所有功能：登录、做题、复习、统计、管理后台
```

### 上线

```bash
# 验证通过后，在服务器上
make preview-stop           # 关掉预览
make deploy                 # 备份 + 上线
```

### 回滚

```bash
make rollback               # 一键回滚
```

## 八、注意事项

| 场景 | 做法 |
|---|---|
| 预览和线上共享同一个数据库 | 预览前先 `make backup`，防止误操作破坏数据 |
| 预览端口 :32222 只监听 127.0.0.1 | 外面完全访问不到，只有 SSH 隧道能连 |
| 重构期间不要 merge 到 main | 全做完、验证通过再 merge |
| 每次 `make preview` 前自动关闭旧预览 | 不会出现多个预览进程冲突 |
