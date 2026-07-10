# KeyIn（刻印）— 项目指南

## 项目概述

多科目在线刷题/备考平台，面向软考（计算机技术与软件专业技术资格考试）。核心特色是集成 **FSRS 间隔重复算法**，科学安排复习节奏，将知识"刻印"到长期记忆。

- **路径**：`/keyin`
- **端口**：32220（生产）/ 32222（预览）
- **数据库**：`database.db`（SQLite，~97MB，~60,000 道题，26 个科目）
- **版本**：见 `VERSION` 文件

---

## 技术栈

| 层 | 技术 |
|----|------|
| 框架 | Python 3.12 + Flask 3.x |
| 数据库 | SQLite3（线程局部连接池，fork 安全） |
| 模板 | Jinja2 + Chart.js |
| 部署 | Gunicorn + systemd + Nginx |
| 限流 | Flask-Limiter（内存存储） |
| 算法 | FSRS 间隔重复（零依赖，纯公式实现） |

---

## 架构分层

```
表现层    templates/ + static/         Jinja2 模板 + Chart.js 图表
路由层    app.py (用户) + admin.py (管理)  所有 HTTP 端点
中间件层  auth.py                      认证/授权装饰器
模型层    models.py (4192行)            全部 DB 操作 + FSRS 算法
持久层    lib/db.py + SQLite            线程局部连接管理
```

---

## 核心文件

| 文件 | 职责 | 注意事项 |
|------|------|----------|
| `models.py` | 数据访问层，FSRS 算法，全部 SQL | 所有 DB 操作必须通过此文件 |
| `app.py` | 用户端路由（刷题、考试、统计、通知） | ~2100 行 |
| `admin.py` | 管理后台 Blueprint（用户/科目/题目/导入/权限） | 1789 行 |
| `auth.py` | 认证中间件 | login_required / admin_required / subject_required |
| `lib/db.py` | SQLite 连接管理 | 线程局部缓存 + fork 安全 |

---

## 常用命令

```bash
# 开发启动
cd /keyin && source venv/bin/activate && python3 app.py

# 预览（SSH 隧道访问）
make preview          # 启动 :32222
make preview-stop     # 停止
make preview-log      # 查看日志

# 部署
make backup           # 备份数据库 + 代码
make deploy           # 备份 → 合并 refactor→main → 重启 → 健康检查
make rollback         # 列出备份
make do-rollback      # 恢复指定备份

# 服务管理
sudo systemctl start/stop/restart keyin
sudo journalctl -u keyin -f

# 数据库备份
cp database.db database.db.bak.$(date +%Y%m%d_%H%M%S)
```

---

## 开发约定

1. **所有 DB 操作通过 models.py**，不直接写 SQL
2. **密码哈希**：Werkzeug pbkdf2:sha256（兼容旧版 sha256，登录时自动升级）
3. **软删除**：`status=0` 标记删除，不物理删除
4. **JSON 字段**：`questions.options` 存为 JSON 字符串，需 `json.loads()`
5. **HTML 净化**：所有用户文本经 `sanitize_html()` 过滤危险标签
6. **字段白名单**：动态 UPDATE 使用 `_ALLOWED_*_FIELDS` 防 SQL 注入
7. **参数化查询**：全部使用 `?` 占位符
8. **单设备登录**：session_token 验证，新登录踢掉旧会话
9. **分支策略**：`main`（生产）/ `refactor`（开发）

---

## FSRS 间隔重复系统

### 核心概念

| 概念 | 含义 | 范围 |
|------|------|------|
| 稳定性 (S) | 记忆维持到 90% 留存的天数 | 0.1 ~ ∞ |
| 难度 (D) | 题目固有难度 | 1.0 ~ 10.0 |
| 目标留存率 (R) | 期望的回忆概率 | 0.7 ~ 0.95（默认 0.9） |
| 衰减系数 | 遗忘曲线参数 | 固定 0.9 |

### 5 级评分

| 评分 | 标签 | 含义 | FSRS 影响 |
|------|------|------|-----------|
| 0 | 忘了 | 完全想不起 | S→30%，D+0.6 |
| 1 | 模糊 | 有印象但不确定 | S→30%，D+0.3 |
| 2 | 一般 | 想起来了 | S 小幅增长，D-0.1 |
| 3 | 简单 | 轻松答对 | S 中幅增长，D-0.4 |
| 4 | 秒答 | 条件反射级 | S 大幅增长，D-0.6 |

### 卡片状态机

```
新题 ──→ 学习(learning) ──→ 复习(review) ──→ 强化(reinforce) ──→ 掌握(mastered)
         step=2, 需连续正确        FSRS 公式排程      reps≥9 或主动进入
```

### 掌握标准

`stability ≥ 45 AND repetitions ≥ 3`（3 周不复习仍 90% 留存）

### 关键常量

```python
FSRS_DECAY = 0.9              # 遗忘曲线衰减系数
FSRS_GAIN_FACTOR = 2.5        # 稳定性增长因子
LEARNING_STEPS = [1, 10]      # 学习步骤（分钟）
RELEARNING_STABILITY_KEEP = 0.3  # 答错保留 30% 稳定性
```

---

## 数据库核心表

| 表 | 用途 | 关键字段 |
|----|------|----------|
| `users` | 用户 | username, password_hash, role, session_token, security_question/answer |
| `subjects` | 科目 | name, code, icon, level, status |
| `categories` | 3 级分类树 | parent_id(0=根), level(1/2/3), sort_order |
| `questions` | 题库 | id(TEXT,格式N.N-N), stem, options(JSON), answer, qtype, subject_id, category_id |
| `review_schedule` | FSRS 状态 | stability, difficulty, card_state, learning_step, next_review |
| `history` | 答题历史 | user_answer, correct, source(practice/exam/mock) |
| `user_licenses` | 时限授权 | expires_at |
| `user_subjects` | 权限 | can_practice, can_mock, can_daily, can_manage |
| `study_limits` | 每日限额 | daily_new_limit(10), daily_review_limit(50) |
| `invitation_codes` | 邀请码 | 格式 KEYIN-XXXX-XXXX |
| `import_staging` | 导入暂存 | 两阶段导入（暂存→确认） |
| `notifications` | 站内通知 | content, is_read |

---

## 路由概览

### 用户端 (app.py)

| 路由 | 功能 |
|------|------|
| `/login` `/register` `/logout` | 认证 |
| `/` | 首页（科目列表） |
| `/subjects/<id>/practice` | 章节练习入口 |
| `/subjects/<id>/study/<cat_id>/setup` | 学习设置页（今日复习/进度/卡片） |
| `/subjects/<id>/study/<cat_id>/today` | 今日复习 |
| `.../practice/<qid>` | 答题 |
| `.../practice/<qid>/answer` (POST) | 提交答案 |
| `.../practice/<qid>/rate` (POST) | FSRS 评分 |
| `/subjects/<id>/exam` | 考试模式 |
| `/subjects/<id>/mock` | 模拟考试 |
| `/subjects/<id>/favorites` | 收藏 |
| `/subjects/<id>/wrong` | 错题 |
| `/subjects/<id>/exams` | 历年真题 |
| `/subjects/<id>/statistics` | 统计可视化 |
| `/subjects/<id>/stats/api` | 统计 JSON API |
| `/notifications` | 通知中心 |

### 管理端 (admin.py, 前缀 /admin)

| 路由 | 功能 |
|------|------|
| `/admin/` | 仪表盘 |
| `/admin/users` | 用户管理 |
| `/admin/subjects` | 科目管理 |
| `/admin/questions` | 题目管理（搜索/分页） |
| `/admin/import` | CSV 导入 |
| `/admin/import-apkg` | Anki .apkg 导入 |
| `/admin/import-staging` | 导入暂存区 |
| `/admin/permissions` | 权限管理 |
| `/admin/licenses` | 许可证管理 |
| `/admin/codes` | 邀请码管理 |
| `/admin/feedbacks` | 反馈管理 |
| `/admin/comments-manage` | 评论管理 |
| `/admin/settings` | 站点设置 |
| `/admin/batch` | 批量操作 |
| `/admin/health` | 数据健康检查 |

---

## 题目类型

| 类型 | qtype | 显示方式 |
|------|-------|----------|
| 单选 | `single` | 标准选择 |
| 多选 | `multiple` | 多选，部分正确按比例计分 |
| 判断 | `judge` | 对/错 |
| 案例分析 | 无 options | 学习卡片模式（不评分，不影响 FSRS） |
| 论述 | 无 options | 学习卡片模式 |

区分案例/论述：`question.options` 为空即为卡片模式。

---

## 数据来源

- **ruankaodaren.com**（软考达人）：20 科目，60,358 道章节题
- **ruantiku.com**（软题库）：历年真题
- 导入脚本：`scripts/import_ruankao.py`、`scripts/import_ruankao_batch.py`、`scripts/import_ruantiku_exam.py`
- 爬虫脚本：`scripts/ruantiku_spider_full.py`

---

## 已知问题（代码审查 2026-05-05）

### 🔴 P0（需立即修复）

1. **安全问答明文存储** — `security_answer` 应使用 `hash_password()` 哈希
2. **模板 `|safe` XSS 风险** — 应使用 `bleach` 库净化或导入时净化
3. **缺少 CSRF 保护** — 所有 POST 表单无 CSRF token，需引入 flask-wtf
4. **路由名称不匹配** — `admin.admin_users` 应为 `admin.users`

### 🟡 P1（尽快修复）

5. `update_review_schedule()` 过长（200+ 行），需拆分
6. `_extract_apkg()` 职责过多，需拆分
7. Flask/Werkzeug 版本需升级（Werkzeug 有 CVE-2023-46136）

---

## 迁移脚本

| 脚本 | 用途 |
|------|------|
| `scripts/migrate.py` | 主 schema 迁移（多科目/多用户/权限） |
| `scripts/migrate_history_to_fsrs.py` | 从历史答题记录重建 FSRS 状态 |
| `scripts/migrate_admin_features.py` | 添加 import_logs 表 |
| `scripts/match_explanations.py` | 匹配练习题解析到真题 |

---

## Git 分支

| 分支 | 用途 |
|------|------|
| `main` | 生产版本，运行在 :32220 |
| `refactor` | 开发/重构分支 |

部署流程：refactor 开发 → 预览验证 → `make deploy`（合并到 main + 重启）
