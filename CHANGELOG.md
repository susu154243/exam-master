# EXAM-MASTER 变更日志

## v0.5 - 2026-04-27
**Anki 题库导入 + 版本追踪**
- 解析 .colpkg 格式题库 (Zstd + protobuf)
- 导入 267 道单选题 (含 31 张 Base64 图片)
- 清空旧测试题 (881 道)
- 新增 VERSION + CHANGELOG 版本追踪
- 初始化 Git 版本控制

## v0.4 - 2026-04-27
**统计可视化模块**
- 新增统计页面 `/subjects/<id>/statistics`
- 新增统计 API `/subjects/<id>/stats/api`
- 6 张概览卡片：连续天数/今日复习/待复习/7天正确率/累计复习/学习分钟
- 4 种图表：学习热力图(90天)/每日趋势双轴图/分类掌握度/保留率曲线
- 新增 models.py 统计函数：get_stats_summary, get_daily_trend, get_heatmap_data, get_category_mastery, get_retention_curve
- 依赖：Chart.js (CDN)

## v0.3 - 2026-04-27
**SM-2 间隔重复刷题**
- 新增 review_schedule 表 (用户-题目复习计划)
- SM-2 算法实现 (models.py: sm2_schedule, get_due_questions, get_new_questions)
- 答题页面新增 5 点评分界面 (😭😕😐😊🤩)
- 优先展示到期题目，不足补充新题
- 复习进度条 (总题数/已复习/待复习)
- 评分后自动跳转下一题

## v0.2 - 2026-04-27
**多租户 + 分类树**
- 数据库迁移：新增 subjects, categories, user_subjects 表
- 三级分类树 (科目 → 二级分类 → 三级知识点)
- 用户-科目权限控制 (@subject_required 中间件)
- 科目导航页面
- 修复 ON CONFLICT 错误 (改用 SELECT-then-INSERT/UPDATE)

## v0.1 - 2026-04-27
**初始部署**
- Flask + SQLite + Gunicorn + systemd + Nginx
- 管理后台独立页面 (admin Blueprint)
- 用户认证 (Flask session + @login_required, @admin_required)
- 答题模式：章节练习/随机答题/模拟考试/错题回顾
- 收藏/历史记录功能
- 管理功能：用户管理/科目管理/题目管理/导入导出
- 密码双兼容 (Werkzeug pbkdf2 + hashlib sha256)
