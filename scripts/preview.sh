#!/bin/bash
# 预览服务管理脚本
# 用法: preview.sh start|stop|status

PORT=32222
PID_FILE=/tmp/keyin_preview.pid
LOG_FILE=/tmp/keyin_preview.log

start() {
    # 关闭已有的预览进程
    if [ -f "$PID_FILE" ]; then
        old_pid=$(cat "$PID_FILE")
        if kill -0 "$old_pid" 2>/dev/null; then
            echo "关闭已有预览进程 (PID: $old_pid)"
            kill "$old_pid" 2>/dev/null
            sleep 1
        fi
    fi
    pkill -f "gunicorn.*:$PORT" 2>/dev/null || true

    # 启动新进程（使用 venv 中的 gunicorn）
    cd /keyin
    source /keyin/venv/bin/activate
    nohup gunicorn -w 2 -b 127.0.0.1:$PORT app:app > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"

    # 等待启动
    sleep 2
    if curl -s -o /dev/null "http://127.0.0.1:$PORT/"; then
        echo "预览已启动: http://127.0.0.1:$PORT"
        echo "本地访问: http://localhost:$PORT (需先建立 SSH 隧道)"
        echo "SSH 命令: ssh -L $PORT:127.0.0.1:$PORT root@118.89.184.64"
    else
        echo "启动失败，日志如下:"
        cat "$LOG_FILE"
        exit 1
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        kill "$pid" 2>/dev/null && echo "预览已关闭 (PID: $pid)" || echo "预览进程已不存在"
        rm -f "$PID_FILE"
    else
        pkill -f "gunicorn.*:$PORT" 2>/dev/null && echo "预览已关闭" || echo "预览未运行"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "预览运行中 (PID: $pid)"
            if curl -s -o /dev/null "http://127.0.0.1:$PORT/"; then
                echo "服务响应: 正常"
            else
                echo "服务响应: 异常"
            fi
        else
            echo "PID 文件存在但进程已死"
        fi
    else
        echo "预览未运行"
    fi
}

case "${1:-}" in
    start) start ;;
    stop) stop ;;
    status) status ;;
    *)
        echo "用法: $0 start|stop|status"
        exit 1
        ;;
esac
