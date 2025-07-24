# WD121_Claude-Discord-Bridge

Discord botを通じてClaude Codeと双方向通信を実現するシステム

## 概要

外出先からスマートフォンのDiscordアプリを使用して、自宅PCで動作するClaude Codeを制御・対話できるシステムです。

## 主な機能

- 📱 スマホからClaude Codeへのコマンド送信
- ✅ 危険なコマンドのリアクションベース承認（✅/❌）
- 🔄 プロセスの自動監視・復旧
- 📊 リアルタイムステータス通知
- 🤖 マルチエージェント対応（president, boss1, worker1-3）

## システム構成

```
Discord（スマホ） ←→ Discord Bot ←→ ファイルシステム ←→ Claude Code（WSL2）
                          ↓
                    tmux内で4つのプロセスが常時稼働
                    1. discord_bridge.py（通信）
                    2. monitor.py（監視）
                    3. claude.py（実行）
                    4. supervisor.sh（プロセス管理）
```

## 必要要件

- Windows PC（WSL2インストール済み）
- Python 3.8以上
- tmux
- Discord Bot Token

## クイックスタート

### 1. 初回セットアップ

```bash
# リポジトリをクローン
cd /mnt/d
git clone https://github.com/NSada2025/WD121_Claude-Discord-Bridge.git
cd WD121_Claude-Discord-Bridge

# セットアップスクリプト実行
chmod +x setup.sh
./setup.sh
```

### 2. Discord Bot設定

1. [Discord Developer Portal](https://discord.com/developers/applications)でBotを作成
2. Bot Tokenを取得
3. `.env`ファイルにTokenを設定

```env
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
```

### 3. システム起動

```bash
./scripts/start_system.sh
```

## 使用方法

### 基本コマンド

- `/execute [command]` - コマンド実行
- `/status` - システム状態確認
- `/restart [process]` - プロセス再起動
- `/logs [process]` - ログ表示

### マルチエージェントコマンド

- `/send president "message"` - presidentへメッセージ送信
- `/send boss1 "message"` - boss1へメッセージ送信

## ディレクトリ構成

```
WD121_Claude-Discord-Bridge/
├── bot/                 # Discord bot関連
│   └── discord_bridge.py
├── bridge/             # 通信ブリッジ
│   ├── monitor.py
│   └── claude.py
├── scripts/            # 各種スクリプト
│   ├── setup.sh
│   ├── start_system.sh
│   └── supervisor.sh
├── logs/               # ログファイル
├── tests/              # テストコード
└── docs/               # ドキュメント
```

## トラブルシューティング

### プロセスが起動しない場合

```bash
# tmuxセッション確認
tmux ls

# 手動でセッション作成
tmux new -s claude-discord
```

### Discord Botがオフラインの場合

1. `.env`ファイルのTokenを確認
2. ネットワーク接続を確認
3. `logs/discord_bridge.log`を確認

## セキュリティ

- Bot Tokenは絶対に公開しない
- `.env`ファイルは`.gitignore`に含める
- 実行可能コマンドは必要に応じて制限

## ライセンス

MIT License

## 作者

NSada2025