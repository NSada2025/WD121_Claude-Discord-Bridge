#!/usr/bin/env python3
"""
コマンド実行エンジン
ファイルからコマンドを読み取り、実行し、結果を返す
"""

import os
import sys
import subprocess
import logging
import signal
import time
from pathlib import Path
from typing import Dict, Any, Optional

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from bridge.file_comm import FileCommunicator, FileWatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/command_executor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CommandExecutor:
    """コマンド実行クラス"""
    
    # 危険なコマンドのパターン
    DANGEROUS_PATTERNS = [
        'rm -rf /',
        'rm -rf ~',
        'dd if=/dev/zero',
        'mkfs',
        ':(){ :|:& };:',  # Fork bomb
        'sudo rm',
        'chmod -R 000',
        '> /dev/sda',
    ]
    
    def __init__(self):
        self.comm = FileCommunicator()
        self.running = True
        self.command_watcher = None
        
    def is_dangerous_command(self, command: str) -> bool:
        """危険なコマンドかチェック"""
        command_lower = command.lower().strip()
        
        # 明らかに危険なパターン
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in command_lower:
                return True
        
        # sudoを含む場合
        if 'sudo' in command_lower:
            return True
        
        # パイプやリダイレクトで危険な操作
        if '>' in command and ('/dev/' in command or '/sys/' in command):
            return True
        
        return False
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """コマンドを実行"""
        try:
            # タイムアウト設定（5分）
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=os.path.expanduser("~")
            )
            
            return {
                'success': True,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command timed out after 5 minutes'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_command_file(self, filepath: Path):
        """コマンドファイルを処理"""
        logger.info(f"Processing command file: {filepath}")
        
        # ファイル読み込み
        data = self.comm.read_json_safe(filepath)
        if not data:
            logger.error(f"Failed to read command file: {filepath}")
            filepath.unlink()
            return
        
        command = data.get('command', '')
        user_name = data.get('user_name', 'unknown')
        
        # 危険なコマンドチェック
        if self.is_dangerous_command(command):
            logger.warning(f"Dangerous command detected: {command}")
            
            # 承認待ちファイル作成
            pending_file = self.comm.create_pending(
                command=command,
                message=f"⚠️ 危険なコマンドが検出されました:\\n`{command}`\\n\\n実行してもよろしいですか？",
                original_file=filepath.name,
                user_name=user_name
            )
            
            if pending_file:
                logger.info(f"Created pending file: {pending_file}")
            
            # 元のコマンドファイルは保持（承認後に実行するため）
            return
        
        # 安全なコマンドは即実行
        logger.info(f"Executing command: {command}")
        result = self.execute_command(command)
        
        # 結果をレスポンスファイルに書き込み
        if result['success']:
            message = f"**コマンド実行完了**\\n`{command}`\\n\\n"
            
            if result['stdout']:
                message += f"**出力:**\\n```\\n{result['stdout'][:1000]}\\n```"
                if len(result['stdout']) > 1000:
                    message += "\\n*(出力は1000文字で切り詰められました)*"
            
            if result['stderr']:
                message += f"\\n\\n**エラー出力:**\\n```\\n{result['stderr'][:500]}\\n```"
            
            self.comm.create_response(
                message=message,
                status='success',
                command=command,
                returncode=result['returncode']
            )
        else:
            self.comm.create_response(
                message=f"**コマンド実行失敗**\\n`{command}`\\n\\nエラー: {result['error']}",
                status='error',
                command=command,
                error=result['error']
            )
        
        # 処理済みファイルを削除
        filepath.unlink()
        logger.info(f"Command processed and file deleted: {filepath}")
    
    def handle_approval_response(self, approval_file: Path):
        """承認レスポンスを処理"""
        logger.info(f"Processing approval response: {approval_file}")
        
        data = self.comm.read_json_safe(approval_file)
        if not data:
            approval_file.unlink()
            return
        
        # 対応する pending ファイルを探す
        pending_filename = approval_file.name.replace('approval_pending_', 'pending_')
        pending_files = list(self.comm.pending_dir.glob(f"{pending_filename}*"))
        
        if not pending_files:
            logger.warning(f"No pending file found for approval: {approval_file}")
            approval_file.unlink()
            return
        
        # pending ファイルから元のコマンド情報を取得
        pending_data = self.comm.read_json_safe(pending_files[0])
        if not pending_data:
            approval_file.unlink()
            return
        
        # 承認された場合
        if data.get('approval', False):
            command = pending_data.get('command', '')
            logger.info(f"Command approved, executing: {command}")
            
            # コマンド実行
            result = self.execute_command(command)
            
            # 結果を送信
            if result['success']:
                message = f"**承認されたコマンドを実行しました**\\n`{command}`\\n\\n"
                if result['stdout']:
                    message += f"**出力:**\\n```\\n{result['stdout'][:1000]}\\n```"
                self.comm.create_response(message=message, status='success')
            else:
                self.comm.create_response(
                    message=f"**コマンド実行失敗**\\n`{command}`\\n\\nエラー: {result['error']}",
                    status='error'
                )
        else:
            # 拒否された場合
            logger.info("Command rejected by user")
            self.comm.create_response(
                message="コマンドの実行がキャンセルされました。",
                status='cancelled'
            )
        
        # 元のコマンドファイルがあれば削除
        original_file = pending_data.get('original_file')
        if original_file:
            original_path = self.comm.command_dir / original_file
            if original_path.exists():
                original_path.unlink()
        
        # クリーンアップ
        approval_file.unlink()
        pending_files[0].unlink()
    
    def start(self):
        """実行エンジンを開始"""
        logger.info("Starting command executor...")
        
        # シグナルハンドラ設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # コマンドファイル監視開始
        self.command_watcher = FileWatcher(
            self.comm.command_dir,
            self.process_command_file
        )
        self.command_watcher.start()
        
        # 承認レスポンス監視
        self.approval_watcher = FileWatcher(
            self.comm.response_dir,
            lambda f: self.handle_approval_response(f) if f.name.startswith('approval_') else None
        )
        self.approval_watcher.start()
        
        logger.info("Command executor started. Waiting for commands...")
        
        # メインループ
        try:
            while self.running:
                time.sleep(1)
                
                # 定期的なクリーンアップ（1時間ごと）
                if int(time.time()) % 3600 == 0:
                    self.comm.cleanup_old_files(hours=24)
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()
    
    def stop(self):
        """実行エンジンを停止"""
        logger.info("Stopping command executor...")
        self.running = False
        
        if self.command_watcher:
            self.command_watcher.stop()
        if self.approval_watcher:
            self.approval_watcher.stop()
        
        logger.info("Command executor stopped")
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラ"""
        logger.info(f"Received signal {signum}")
        self.running = False


def main():
    """メイン関数"""
    executor = CommandExecutor()
    executor.start()


if __name__ == "__main__":
    main()