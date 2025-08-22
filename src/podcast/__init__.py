# -*- coding: utf-8 -*-

"""
ポッドキャスト機能パッケージ
"""

from .script_generator import DialogueScriptGenerator

# 音声処理系コンポーネントは条件付きインポート（依存関係の問題を回避）
try:
    from .tts_engine import GeminiTTSEngine
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    
try:
    from .audio_processor import AudioProcessor
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False
    
try:
    from .publisher import PodcastPublisher
    PUBLISHING_AVAILABLE = True
except ImportError:
    PUBLISHING_AVAILABLE = False

# 利用可能なコンポーネントのみをエクスポート
__all__ = ["DialogueScriptGenerator"]

if TTS_AVAILABLE:
    __all__.append("GeminiTTSEngine")
if AUDIO_PROCESSING_AVAILABLE:
    __all__.append("AudioProcessor")
if PUBLISHING_AVAILABLE:
    __all__.append("PodcastPublisher")
