#!/usr/bin/env python3
"""
Discord Bridge - Claude Code通信用Discord Bot
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/discord_bridge.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 設定
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_GUILD_ID = int(os.getenv('DISCORD_GUILD_ID', 0))
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))
COMM_DIR = Path(os.getenv('COMM_DIR', '/tmp/claude-discord'))

# 通信ディレクトリの確認
COMMAND_DIR = COMM_DIR / 'commands'
RESPONSE_DIR = COMM_DIR / 'responses'
PENDING_DIR = COMM_DIR / 'pending'

# ディレクトリ作成
for dir_path in [COMMAND_DIR, RESPONSE_DIR, PENDING_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

class ClaudeBridge(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.guild_id = DISCORD_GUILD_ID
        self.channel_id = DISCORD_CHANNEL_ID
        self.pending_confirmations = {}
        
    async def setup_hook(self):
        """Bot起動時の初期設定"""
        # スラッシュコマンドの同期
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Commands synced to guild {self.guild_id}")
        else:
            await self.tree.sync()
            logger.info("Commands synced globally")
    
    async def on_ready(self):
        """Bot準備完了時"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Guild ID: {self.guild_id}')
        logger.info(f'Channel ID: {self.channel_id}')
        
        # バックグラウンドタスク開始
        if not check_pending.is_running():
            check_pending.start()
        if not check_responses.is_running():
            check_responses.start()
        
        # 起動通知
        if self.channel_id:
            channel = self.get_channel(self.channel_id)
            if channel:
                embed = discord.Embed(
                    title="🟢 システム起動",
                    description="Claude Discord Bridgeが起動しました",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)

# Botインスタンス作成
bot = ClaudeBridge()

@bot.tree.command(name="execute", description="Claude Codeでコマンドを実行")
@app_commands.describe(command="実行するコマンド")
async def execute(interaction: discord.Interaction, command: str):
    """コマンド実行"""
    await interaction.response.defer()
    
    # コマンドファイル作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    command_file = COMMAND_DIR / f"cmd_{timestamp}.json"
    
    command_data = {
        "command": command,
        "user_id": str(interaction.user.id),
        "user_name": interaction.user.name,
        "timestamp": timestamp,
        "channel_id": str(interaction.channel_id)
    }
    
    with open(command_file, 'w') as f:
        json.dump(command_data, f, indent=2)
    
    embed = discord.Embed(
        title="📤 コマンド送信",
        description=f"```{command}```",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"実行者: {interaction.user.name}")
    
    await interaction.followup.send(embed=embed)
    logger.info(f"Command sent: {command} by {interaction.user.name}")

@bot.tree.command(name="status", description="システムの状態を確認")
async def status(interaction: discord.Interaction):
    """ステータス確認"""
    await interaction.response.defer()
    
    # 各ディレクトリのファイル数を確認
    cmd_count = len(list(COMMAND_DIR.glob("*.json")))
    res_count = len(list(RESPONSE_DIR.glob("*.json")))
    pending_count = len(list(PENDING_DIR.glob("*.json")))
    
    embed = discord.Embed(
        title="📊 システムステータス",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(name="📥 待機中のコマンド", value=f"{cmd_count}件", inline=True)
    embed.add_field(name="📤 未送信の応答", value=f"{res_count}件", inline=True)
    embed.add_field(name="⏳ 承認待ち", value=f"{pending_count}件", inline=True)
    
    # 通信ディレクトリの存在確認
    embed.add_field(
        name="📁 通信ディレクトリ",
        value="✅ 正常" if COMM_DIR.exists() else "❌ エラー",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

@tasks.loop(seconds=1)
async def check_pending():
    """承認待ちメッセージの確認"""
    try:
        for pending_file in PENDING_DIR.glob("*.json"):
            try:
                with open(pending_file, 'r') as f:
                    data = json.load(f)
                
                # 既に処理済みかチェック
                if pending_file.name in bot.pending_confirmations:
                    continue
                
                # 承認要求メッセージ送信
                channel = bot.get_channel(bot.channel_id)
                if channel:
                    embed = discord.Embed(
                        title="⚠️ 承認が必要です",
                        description=data.get('message', '不明なコマンド'),
                        color=discord.Color.yellow(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(
                        name="コマンド",
                        value=f"```{data.get('command', 'N/A')}```",
                        inline=False
                    )
                    
                    message = await channel.send(embed=embed)
                    
                    # リアクション追加
                    await message.add_reaction("✅")
                    await message.add_reaction("❌")
                    
                    # 管理辞書に追加
                    bot.pending_confirmations[pending_file.name] = {
                        'message': message,
                        'file': pending_file,
                        'data': data
                    }
                    
                    logger.info(f"Pending confirmation sent: {pending_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing pending file {pending_file}: {e}")
                
    except Exception as e:
        logger.error(f"Error in check_pending: {e}")

@tasks.loop(seconds=1)
async def check_responses():
    """レスポンスファイルの確認"""
    try:
        for response_file in RESPONSE_DIR.glob("*.json"):
            try:
                with open(response_file, 'r') as f:
                    data = json.load(f)
                
                # チャンネルに送信
                channel = bot.get_channel(bot.channel_id)
                if channel:
                    embed = discord.Embed(
                        title="📨 応答",
                        description=data.get('message', ''),
                        color=discord.Color.green() if data.get('status') == 'success' else discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    
                    if 'error' in data:
                        embed.add_field(name="エラー", value=data['error'], inline=False)
                    
                    await channel.send(embed=embed)
                    
                # 送信済みファイルを削除
                response_file.unlink()
                logger.info(f"Response sent and deleted: {response_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing response file {response_file}: {e}")
                
    except Exception as e:
        logger.error(f"Error in check_responses: {e}")

@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    """リアクション追加時の処理"""
    # Bot自身のリアクションは無視
    if user.bot:
        return
    
    # 承認待ちメッセージの確認
    for filename, info in list(bot.pending_confirmations.items()):
        if info['message'].id == reaction.message.id:
            if str(reaction.emoji) == "✅":
                # 承認
                approval_file = RESPONSE_DIR / f"approval_{filename}"
                with open(approval_file, 'w') as f:
                    json.dump({
                        "approval": True,
                        "user_id": str(user.id),
                        "user_name": user.name,
                        "timestamp": datetime.now().isoformat()
                    }, f)
                
                # 承認通知
                embed = discord.Embed(
                    title="✅ 承認されました",
                    description=f"{user.name}が実行を承認しました",
                    color=discord.Color.green()
                )
                await reaction.message.edit(embed=embed)
                
                # 元のファイルを削除
                info['file'].unlink()
                del bot.pending_confirmations[filename]
                
            elif str(reaction.emoji) == "❌":
                # 拒否
                approval_file = RESPONSE_DIR / f"approval_{filename}"
                with open(approval_file, 'w') as f:
                    json.dump({
                        "approval": False,
                        "user_id": str(user.id),
                        "user_name": user.name,
                        "timestamp": datetime.now().isoformat()
                    }, f)
                
                # 拒否通知
                embed = discord.Embed(
                    title="❌ 拒否されました",
                    description=f"{user.name}が実行を拒否しました",
                    color=discord.Color.red()
                )
                await reaction.message.edit(embed=embed)
                
                # 元のファイルを削除
                info['file'].unlink()
                del bot.pending_confirmations[filename]

# エラーハンドリング
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """スラッシュコマンドエラー時の処理"""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"コマンドはクールダウン中です。{error.retry_after:.2f}秒後に再試行してください。",
            ephemeral=True
        )
    else:
        logger.error(f"Command error: {error}")
        await interaction.response.send_message(
            "コマンド実行中にエラーが発生しました。",
            ephemeral=True
        )

def main():
    """メイン関数"""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables")
        sys.exit(1)
    
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()