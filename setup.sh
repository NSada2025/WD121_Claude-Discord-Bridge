#!/bin/bash

# WD121_Claude-Discord-Bridge Setup Script

echo "================================================"
echo "WD121 Claude-Discord Bridge セットアップ"
echo "================================================"

# 色の定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 現在のディレクトリ確認
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "\n${GREEN}[1/7] 必要なパッケージの確認${NC}"

# Python確認
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}エラー: Python3がインストールされていません${NC}"
    echo "以下のコマンドでインストールしてください:"
    echo "sudo apt update && sudo apt install python3 python3-pip"
    exit 1
fi

# tmux確認
if ! command -v tmux &> /dev/null; then
    echo -e "${YELLOW}tmuxをインストールします...${NC}"
    sudo apt update && sudo apt install -y tmux
fi

echo -e "${GREEN}[2/7] Python仮想環境の作成${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "仮想環境を作成しました"
fi

# 仮想環境の有効化
source venv/bin/activate

echo -e "\n${GREEN}[3/7] Pythonパッケージのインストール${NC}"
pip install --upgrade pip

# requirements.txtの作成
cat > requirements.txt << EOF
discord.py>=2.3.0
python-dotenv>=1.0.0
aiofiles>=23.0.0
watchdog>=3.0.0
psutil>=5.9.0
EOF

pip install -r requirements.txt

echo -e "\n${GREEN}[4/7] 通信用ディレクトリの作成${NC}"
COMM_DIR="/tmp/claude-discord"
if [ ! -d "$COMM_DIR" ]; then
    mkdir -p "$COMM_DIR/commands"
    mkdir -p "$COMM_DIR/responses"
    mkdir -p "$COMM_DIR/pending"
    chmod 700 "$COMM_DIR"
    echo "通信用ディレクトリを作成しました: $COMM_DIR"
fi

echo -e "\n${GREEN}[5/7] 環境変数ファイルの準備${NC}"
if [ ! -f ".env" ]; then
    cat > .env.example << EOF
# Discord Bot設定
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
DISCORD_CHANNEL_ID=your_channel_id_here

# システム設定
LOG_LEVEL=INFO
COMMAND_TIMEOUT=300
CHECK_INTERVAL=1

# ファイルパス
COMM_DIR=/tmp/claude-discord
LOG_DIR=./logs
EOF
    
    cp .env.example .env
    echo -e "${YELLOW}重要: .envファイルにDiscord Botの情報を設定してください${NC}"
    echo "設定項目:"
    echo "  - DISCORD_TOKEN: Botのトークン"
    echo "  - DISCORD_GUILD_ID: サーバーID"
    echo "  - DISCORD_CHANNEL_ID: チャンネルID"
fi

echo -e "\n${GREEN}[6/7] 実行権限の設定${NC}"
chmod +x setup.sh
chmod +x scripts/*.sh 2>/dev/null || true

echo -e "\n${GREEN}[7/7] ログディレクトリの確認${NC}"
mkdir -p logs
touch logs/.gitkeep

echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}セットアップが完了しました！${NC}"
echo -e "${GREEN}================================================${NC}"
echo
echo "次のステップ:"
echo "1. Discord Developer PortalでBotを作成"
echo "2. .envファイルにBot情報を設定"
echo "3. ./scripts/start_system.sh でシステムを起動"
echo
echo -e "${YELLOW}注意: 初回起動前に必ず.envファイルを設定してください${NC}"