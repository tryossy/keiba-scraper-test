"""
エラーハンドリングユーティリティ
"""
import functools
import traceback
from typing import Callable, Any, Optional, Type, Tuple
from .logger import get_logger


def retry_on_error(max_retries: int = 3, delay: float = 1.0,
                  exceptions: Tuple[Type[Exception], ...] = (Exception,),
                  logger_name: str = 'keiba'):
    """
    エラー時にリトライするデコレータ

    Args:
        max_retries: 最大リトライ回数
        delay: リトライ間隔（秒）
        exceptions: キャッチする例外のタプル
        logger_name: ロガー名

    Usage:
        @retry_on_error(max_retries=3, delay=2.0)
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            last_exception = None

            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"[リトライ {attempt}/{max_retries}] {func.__name__}: {e}"
                        )
                        import time
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"[失敗] {func.__name__}: {max_retries}回のリトライ後も失敗"
                        )

            # 全リトライ失敗
            raise last_exception

        return wrapper
    return decorator


def safe_execute(func: Callable, *args, default: Any = None,
                logger_name: str = 'keiba', **kwargs) -> Any:
    """
    関数を安全に実行し、エラー時はデフォルト値を返す

    Args:
        func: 実行する関数
        *args: 関数の引数
        default: エラー時の戻り値
        logger_name: ロガー名
        **kwargs: 関数のキーワード引数

    Returns:
        関数の戻り値、またはエラー時はdefault

    Usage:
        result = safe_execute(risky_function, arg1, arg2, default=0)
    """
    logger = get_logger(logger_name)

    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"[エラー] {func.__name__}: {e}")
        logger.debug(f"スタックトレース:\n{traceback.format_exc()}")
        return default


def handle_errors(default: Any = None, log_error: bool = True,
                 logger_name: str = 'keiba'):
    """
    エラーハンドリングデコレータ

    Args:
        default: エラー時の戻り値
        log_error: エラーをログに記録するか
        logger_name: ロガー名

    Usage:
        @handle_errors(default=[])
        def get_race_list():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger = get_logger(logger_name)
                    logger.error(f"[エラー] {func.__name__}: {e}")
                    logger.debug(f"スタックトレース:\n{traceback.format_exc()}")
                return default

        return wrapper
    return decorator


class ErrorCollector:
    """エラーを収集して後でまとめて処理"""

    def __init__(self, logger_name: str = 'keiba'):
        self.errors = []
        self.logger = get_logger(logger_name)

    def add(self, error: Exception, context: str = ''):
        """エラーを追加"""
        self.errors.append({
            'error': error,
            'context': context,
            'type': type(error).__name__,
            'message': str(error),
        })
        self.logger.debug(f"[エラー収集] {context}: {error}")

    def has_errors(self) -> bool:
        """エラーがあるか"""
        return len(self.errors) > 0

    def get_error_count(self) -> int:
        """エラー数を取得"""
        return len(self.errors)

    def get_errors(self) -> list:
        """エラーリストを取得"""
        return self.errors

    def print_summary(self):
        """エラーサマリーを出力"""
        if not self.has_errors():
            self.logger.info("[結果] エラーなし")
            return

        self.logger.error(f"[エラーサマリー] {self.get_error_count()}件のエラー")

        # エラータイプごとに集計
        error_types = {}
        for err in self.errors:
            err_type = err['type']
            if err_type not in error_types:
                error_types[err_type] = 0
            error_types[err_type] += 1

        for err_type, count in error_types.items():
            self.logger.error(f"  - {err_type}: {count}件")

        # 最初の5件を詳細表示
        self.logger.error("\n[詳細] 最初の5件:")
        for i, err in enumerate(self.errors[:5], 1):
            self.logger.error(f"  {i}. {err['context']}: {err['message']}")

    def clear(self):
        """エラーリストをクリア"""
        self.errors.clear()


def validate_input(validator: Callable[[Any], bool], error_msg: str = "Invalid input"):
    """
    入力値を検証するデコレータ

    Args:
        validator: 検証関数（True/Falseを返す）
        error_msg: エラーメッセージ

    Usage:
        @validate_input(lambda x: x > 0, "Value must be positive")
        def process_value(x):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 最初の引数を検証
            if args and not validator(args[0]):
                raise ValueError(f"{func.__name__}: {error_msg}")
            return func(*args, **kwargs)

        return wrapper
    return decorator


# 便利な検証関数
def not_none(value: Any) -> bool:
    """値がNoneでないことを確認"""
    return value is not None


def not_empty(value: Any) -> bool:
    """値が空でないことを確認（文字列、リスト、辞書など）"""
    return value is not None and len(value) > 0


def is_positive(value: float) -> bool:
    """値が正の数であることを確認"""
    return value > 0


def in_range(min_val: float, max_val: float):
    """値が範囲内であることを確認するファクトリ関数"""
    def validator(value: float) -> bool:
        return min_val <= value <= max_val
    return validator
