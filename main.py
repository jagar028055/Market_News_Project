# -*- coding: utf-8 -*-

from dotenv import load_dotenv
from src.core import NewsProcessor
from src.logging_config import setup_logging
from config.base import LoggingConfig

# .envファイルから環境変数を読み込む
load_dotenv()

def main() -> None:
    """
    スクリプト全体のメイン処理を実行する
    """
    # ログ設定
    config = LoggingConfig()
    setup_logging(config)
    
    # ニュース処理実行
    processor = NewsProcessor()
    processor.run()

if __name__ == "__main__":
    main()
