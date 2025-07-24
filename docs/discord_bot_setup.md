# Discord Bot セットアップガイド

## 1. Discord Developer Portalでアプリケーション作成

1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. 「New Application」をクリック
3. アプリケーション名を入力（例：Claude Discord Bridge）
4. 「Create」をクリック

## 2. Bot作成

1. 左側メニューの「Bot」をクリック
2. 「Add Bot」をクリック
3. 「Yes, do it!」をクリック

## 3. Bot設定

### 重要な設定項目：

1. **Bot Token**
   - 「Reset Token」をクリック
   - 表示されたトークンをコピー（一度しか表示されません！）
   - このトークンを`.env`ファイルの`DISCORD_TOKEN`に設定

2. **Privileged Gateway Intents**
   - 「MESSAGE CONTENT INTENT」を**ON**にする（重要！）
   - 「SERVER MEMBERS INTENT」を**ON**にする
   - 「Save Changes」をクリック

## 4. Bot招待リンクの生成

1. 左側メニューの「OAuth2」→「URL Generator」をクリック
2. **SCOPES**で以下を選択：
   - `bot`
   - `applications.commands`

3. **BOT PERMISSIONS**で以下を選択：
   - Send Messages
   - Read Message History
   - Add Reactions
   - Manage Messages
   - Embed Links
   - Use Slash Commands

4. 生成されたURLをコピー

## 5. Botをサーバーに招待

1. 生成されたURLをブラウザで開く
2. 招待先のサーバー（test2）を選択
3. 「認証」をクリック

## 6. 必要な情報の取得

### Guild ID（サーバーID）の取得：
1. Discordアプリで開発者モードを有効化
   - ユーザー設定 → 詳細設定 → 開発者モード をON
2. サーバー名を右クリック → 「IDをコピー」

### Channel IDの取得：
1. 使用するチャンネルを右クリック → 「IDをコピー」

## 7. .envファイルに設定

```env
DISCORD_TOKEN=コピーしたトークン
DISCORD_GUILD_ID=コピーしたサーバーID
DISCORD_CHANNEL_ID=コピーしたチャンネルID
```

## セキュリティ注意事項

- **Bot Tokenは絶対に公開しない**
- GitHubにpushする前に`.env`ファイルが`.gitignore`に含まれているか確認
- Tokenが漏洩した場合は即座に「Reset Token」で再生成