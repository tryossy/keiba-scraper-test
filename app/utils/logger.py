"""
ログユーティリティ - 統一されたログ出力
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class KeibaLogger:
    """競馬アプリケーション用ロガー"""

    def __init__(self, name: str, log_dir: str = 'logs', log_file: Optional[str] = None,
                 level: int = logging.INFO, console: bool = True):
        """
        Args:
            name: ロガー名
            log_dir: ログディレクトリ
            log_file: ログファイル名（Noneの場合は自動生成）
            level: ログレベル
            console: コンソール出力を有効化
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 既存のハンドラをクリア
        if self.logger.handlers:
            self.logger.handlers.clear()

        # フォーマッター
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # コンソールハンドラ
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # ファイルハンドラ
        if log_file or log_dir:
            log_path = self._setup_log_file(log_dir, log_file, name)
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _setup_log_file(self, log_dir: str, log_file: Optional[str], name: str) -> Path:
        """ログファイルのパスを設定"""
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)

        if log_file:
            return log_dir_path / log_file
        else:
            # タイムスタンプ付きファイル名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return log_dir_path / f"{name}_{timestamp}.log"

    def debug(self, msg: str, *args, **kwargs):
        """デバッグログ"""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """情報ログ"""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """警告ログ"""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """エラーログ"""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """クリティカルログ"""
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """例外ログ（スタックトレース付き）"""
        self.logger.exception(msg, *args, **kwargs)


def get_logger(name: str, **kwargs) -> KeibaLogger:
    """
    ロガーを取得

    Args:
        name: ロガー名
        **kwargs: KeibaLoggerのコンストラクタ引数

    Returns:
        KeibaLogger instance
    """
    return KeibaLogger(name, **kwargs)


# グローバルロガーの例
def get_default_logger() -> KeibaLogger:
    """デフォルトロガーを取得"""
    return get_logger('keiba', log_dir='logs', console=True, level=logging.INFO)
