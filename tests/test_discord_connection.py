#!/usr/bin/env python3
"""
Discord接続テストスクリプト
.envファイルの設定が正しいか確認します
"""

import os
import sys
import asyncio
from pathlib import Path

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import discord
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

async def test_connection():
    """Discord接続テスト"""
    token = os.getenv('DISCORD_TOKEN')
    guild_id = os.getenv('DISCORD_GUILD_ID')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    print("=== Discord接続テスト ===")
    print(f"Token: {'設定済み' if token else '未設定'}")
    print(f"Guild ID: {guild_id if guild_id else '未設定'}")
    print(f"Channel ID: {channel_id if channel_id else '未設定'}")
    
    if not token:
        print("\n❌ エラー: DISCORD_TOKENが設定されていません")
        print("1. Discord Developer PortalでBot Tokenを取得")
        print("2. .envファイルにDISCORD_TOKEN=<your_token>を設定")
        return
    
    # 簡易クライアントで接続テスト
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        print(f"\n✅ 接続成功！")
        print(f"Bot名: {client.user}")
        print(f"Bot ID: {client.user.id}")
        
        # Guild確認
        if guild_id:
            guild = client.get_guild(int(guild_id))
            if guild:
                print(f"\n✅ サーバー確認: {guild.name}")
                
                # Channel確認
                if channel_id:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        print(f"✅ チャンネル確認: #{channel.name}")
                    else:
                        print(f"❌ チャンネルID {channel_id} が見つかりません")
            else:
                print(f"❌ サーバーID {guild_id} が見つかりません")
        
        await client.close()
    
    try:
        await client.start(token)
    except discord.LoginFailure:
        print("\n❌ エラー: トークンが無効です")
    except Exception as e:
        print(f"\n❌ エラー: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())