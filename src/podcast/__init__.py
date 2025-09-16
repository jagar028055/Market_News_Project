# -*- coding: utf-8 -*-

"""
ポッドキャスト機能パッケージ
"""

from .script_generator import DialogueScriptGenerator

# 音声処理系コンポーネントをオプショナルインポート（台本確認モードでは不要）
try:
    from .tts_engine import GeminiTTSEngine
    from .audio_processor import AudioProcessor
    from .publisher import PodcastPublisher
    _AUDIO_AVAILABLE = True
except ImportError:
    GeminiTTSEngine = None
    AudioProcessor = None  
    PodcastPublisher = None
    _AUDIO_AVAILABLE = False

__all__ = [
    "DialogueScriptGenerator",
    "GeminiTTSEngine", 
    "AudioProcessor",
    "PodcastPublisher"
]
