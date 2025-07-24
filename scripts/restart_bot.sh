#!/bin/bash

# Bot再起動スクリプト

echo "=== Discord Bot 再起動 ==="

# 1. 現在のプロセスを確認
echo "現在のプロセスを確認中..."
PIDS=$(pgrep -f "discord_bridge.py")

if [ -n "$PIDS" ]; then
    echo "実行中のBotを停止します (PID: $PIDS)"
    kill $PIDS
    sleep 2
    
    # 強制終了が必要な場合
    if pgrep -f "discord_bridge.py" > /dev/null; then
        echo "強制終了します..."
        kill -9 $PIDS
        sleep 1
    fi
else
    echo "実行中のBotは見つかりませんでした"
fi

# 2. プロジェクトディレクトリに移動
cd /mnt/c/Users/Owner/WD121_Claude-Discord-Bridge

# 3. 仮想環境を有効化して起動
echo "Botを起動します..."
source venv/bin/activate
python bot/discord_bridge.py &

# 4. 起動確認
sleep 3
NEW_PID=$(pgrep -f "discord_bridge.py")

if [ -n "$NEW_PID" ]; then
    echo "✅ Bot起動成功！ (PID: $NEW_PID)"
    echo "ログを確認するには: tail -f logs/discord_bridge.log"
else
    echo "❌ Bot起動失敗"
    echo "手動で確認してください"
fi