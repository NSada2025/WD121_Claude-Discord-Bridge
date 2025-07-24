#!/bin/bash

# システム全体の起動スクリプト

echo "=== Claude Discord Bridge システム起動 ==="

# プロジェクトディレクトリ
PROJECT_DIR="/mnt/c/Users/Owner/WD121_Claude-Discord-Bridge"
cd "$PROJECT_DIR"

# 仮想環境の確認
if [ ! -d "venv" ]; then
    echo "❌ 仮想環境が見つかりません。setup.sh を実行してください。"
    exit 1
fi

# tmuxセッションの確認
SESSION_NAME="claude-discord"
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "既存のセッションが見つかりました。停止します..."
    tmux kill-session -t "$SESSION_NAME"
    sleep 2
fi

echo "tmuxセッションを作成します..."

# tmuxセッションを作成し、3つのペインに分割
tmux new-session -d -s "$SESSION_NAME" -n "main"

# ペイン1: Discord Bot
tmux send-keys -t "$SESSION_NAME:0.0" "cd $PROJECT_DIR && source venv/bin/activate" Enter
tmux send-keys -t "$SESSION_NAME:0.0" "echo '=== Discord Bot ===' && python bot/discord_bridge.py" Enter

# 垂直分割
tmux split-window -h -t "$SESSION_NAME:0"

# ペイン2: Command Executor
tmux send-keys -t "$SESSION_NAME:0.1" "cd $PROJECT_DIR && source venv/bin/activate" Enter
tmux send-keys -t "$SESSION_NAME:0.1" "echo '=== Command Executor ===' && python bridge/command_executor.py" Enter

# 水平分割
tmux split-window -v -t "$SESSION_NAME:0.1"

# ペイン3: ログ監視
tmux send-keys -t "$SESSION_NAME:0.2" "cd $PROJECT_DIR" Enter
tmux send-keys -t "$SESSION_NAME:0.2" "echo '=== System Logs ===' && tail -f logs/*.log" Enter

echo ""
echo "✅ システムが起動しました！"
echo ""
echo "tmuxセッションに接続するには:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "セッションから離れるには:"
echo "  Ctrl+B, D"
echo ""
echo "システムを停止するには:"
echo "  tmux kill-session -t $SESSION_NAME"
echo ""
echo "各ペインの説明:"
echo "  左: Discord Bot"
echo "  右上: Command Executor"
echo "  右下: ログ監視"