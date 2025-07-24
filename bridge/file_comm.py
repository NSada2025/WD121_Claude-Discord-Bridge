#!/usr/bin/env python3
"""
ファイル通信の共通ライブラリ
ファイルロック、監視、クリーンアップ機能を提供
"""

import os
import json
import fcntl
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import threading
import queue

logger = logging.getLogger(__name__)

class FileCommunicator:
    """ファイルベース通信を管理するクラス"""
    
    def __init__(self, base_dir: str = "/tmp/claude-discord"):
        self.base_dir = Path(base_dir)
        self.command_dir = self.base_dir / "commands"
        self.response_dir = self.base_dir / "responses"
        self.pending_dir = self.base_dir / "pending"
        
        # ディレクトリ作成
        for dir_path in [self.command_dir, self.response_dir, self.pending_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def write_json_safe(self, filepath: Path, data: Dict[str, Any]) -> bool:
        """ファイルロックを使用して安全にJSONを書き込む"""
        try:
            # 一時ファイルに書き込み
            temp_file = filepath.with_suffix('.tmp')
            
            with open(temp_file, 'w') as f:
                # ファイルロック取得
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(data, f, indent=2, ensure_ascii=False)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            
            # アトミックに移動
            temp_file.replace(filepath)
            return True
            
        except Exception as e:
            logger.error(f"Failed to write {filepath}: {e}")
            if temp_file.exists():
                temp_file.unlink()
            return False
    
    def read_json_safe(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """ファイルロックを使用して安全にJSONを読み込む"""
        try:
            with open(filepath, 'r') as f:
                # 共有ロック
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                data = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return data
        except Exception as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return None
    
    def create_command(self, command: str, user_info: Dict[str, str]) -> str:
        """コマンドファイルを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"cmd_{timestamp}.json"
        filepath = self.command_dir / filename
        
        data = {
            "command": command,
            "timestamp": timestamp,
            "status": "pending",
            **user_info
        }
        
        if self.write_json_safe(filepath, data):
            return filename
        return ""
    
    def create_response(self, message: str, status: str = "success", **kwargs) -> str:
        """レスポンスファイルを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"res_{timestamp}.json"
        filepath = self.response_dir / filename
        
        data = {
            "message": message,
            "status": status,
            "timestamp": timestamp,
            **kwargs
        }
        
        if self.write_json_safe(filepath, data):
            return filename
        return ""
    
    def create_pending(self, command: str, message: str, **kwargs) -> str:
        """承認待ちファイルを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"pending_{timestamp}.json"
        filepath = self.pending_dir / filename
        
        data = {
            "command": command,
            "message": message,
            "timestamp": timestamp,
            "status": "waiting",
            **kwargs
        }
        
        if self.write_json_safe(filepath, data):
            return filename
        return ""
    
    def get_oldest_command(self) -> Optional[tuple[Path, Dict[str, Any]]]:
        """最も古いコマンドファイルを取得"""
        try:
            files = sorted(self.command_dir.glob("cmd_*.json"))
            if files:
                data = self.read_json_safe(files[0])
                if data:
                    return files[0], data
        except Exception as e:
            logger.error(f"Failed to get oldest command: {e}")
        return None
    
    def cleanup_old_files(self, hours: int = 24):
        """古いファイルを削除"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for directory in [self.command_dir, self.response_dir, self.pending_dir]:
            try:
                for filepath in directory.glob("*.json"):
                    if filepath.stat().st_mtime < cutoff_time.timestamp():
                        filepath.unlink()
                        logger.info(f"Cleaned up old file: {filepath}")
            except Exception as e:
                logger.error(f"Cleanup error in {directory}: {e}")


class FileWatcher:
    """ファイル監視クラス（inotifyの代替）"""
    
    def __init__(self, watch_dir: Path, callback):
        self.watch_dir = watch_dir
        self.callback = callback
        self.running = False
        self.thread = None
        self.processed_files = set()
    
    def start(self):
        """監視を開始"""
        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started watching {self.watch_dir}")
    
    def stop(self):
        """監視を停止"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"Stopped watching {self.watch_dir}")
    
    def _watch_loop(self):
        """監視ループ"""
        while self.running:
            try:
                # 新しいファイルをチェック
                for filepath in self.watch_dir.glob("*.json"):
                    if filepath.name not in self.processed_files:
                        self.processed_files.add(filepath.name)
                        self.callback(filepath)
                
                # 削除されたファイルをセットから削除
                existing_files = {f.name for f in self.watch_dir.glob("*.json")}
                self.processed_files &= existing_files
                
            except Exception as e:
                logger.error(f"Watch loop error: {e}")
            
            time.sleep(0.5)  # 0.5秒ごとにチェック