# 刻印部署管理
# 用法: make <命令>

BACKUP_DIR = /keyin/backups
TIMESTAMP = $(shell date +%Y%m%d_%H%M%S)

# 备份数据库 + 当前代码
backup:
	@mkdir -p $(BACKUP_DIR)
	@cp /keyin/database.db $(BACKUP_DIR)/database.db.$(TIMESTAMP)
	@cd /keyin && git bundle create $(BACKUP_DIR)/code.$(TIMESTAMP).bundle HEAD
	@echo "备份完成: $(TIMESTAMP)"

# 启动预览（:32222，仅 127.0.0.1 监听，通过 SSH 隧道本地访问）
preview:
	@/keyin/scripts/preview.sh start

# 关闭预览
preview-stop:
	@/keyin/scripts/preview.sh stop

# 查看预览日志
preview-log:
	@cat /tmp/keyin_preview.log

# 部署上线（备份 → 切 main → merge refactor → 重启）
deploy: backup
	@cd /keyin && git checkout main && git merge refactor && systemctl restart keyin
	@sleep 2
	@curl -s -o /dev/null http://127.0.0.1:32220/ && echo "部署完成" || (echo "部署可能失败，请检查:" && systemctl status keyin | head -10)

# 回滚到指定备份
rollback:
	@echo "用法: make rollback TIMESTAMP=20260529_120000"
	@echo "可用备份:"
	@ls -1 $(BACKUP_DIR)/database.db.* 2>/dev/null | sed 's/.*database.db.//' || echo "  暂无备份"

# 执行回滚（内部命令，通过 rollback 查看备份列表后使用）
do-rollback:
	@cp $(BACKUP_DIR)/database.db.$(TIMESTAMP) /keyin/database.db
	@cd /keyin && git checkout main && systemctl restart keyin
	@echo "回滚完成: $(TIMESTAMP)"

# 列出备份
backup-list:
	@ls -1 $(BACKUP_DIR)/database.db.* 2>/dev/null | sed 's/.*database.db.//' || echo "暂无备份"

.PHONY: backup preview preview-stop preview-log deploy rollback do-rollback backup-list
