# -*- coding: utf-8 -*-

"""
ポッドキャスト統合機能の例外クラス
"""


class PodcastIntegrationError(Exception):
    """ポッドキャスト統合機能の基底例外クラス"""
    pass


class PodcastConfigurationError(PodcastIntegrationError):
    """
    ポッドキャスト設定エラー
    
    必要な環境変数が設定されていない、
    または設定値が無効な場合に発生
    """
    pass


class CostLimitExceededError(PodcastIntegrationError):
    """
    コスト制限超過エラー
    
    月間コスト制限を超過した場合に発生
    """
    pass


class BroadcastError(PodcastIntegrationError):
    """
    LINE配信エラー
    
    LINE Messaging API呼び出しが失敗した場合に発生
    """
    pass


class PodcastGenerationError(PodcastIntegrationError):
    """
    ポッドキャスト生成エラー
    
    台本生成、音声合成、音声処理のいずれかが失敗した場合に発生
    """
    pass


class AudioProcessingError(PodcastIntegrationError):
    """
    音声処理エラー
    
    音声ファイルの処理中にエラーが発生した場合
    """
    pass


class RSSGenerationError(PodcastIntegrationError):
    """
    RSS生成エラー
    
    RSSフィードの生成中にエラーが発生した場合
    """
    pass