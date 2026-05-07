# -*- coding: utf-8 -*-

"""
ポッドキャスト機能パッケージ
"""

# 全コンポーネントをオプショナルインポート（未インストール依存でもインポートエラーを防止）
try:
    from .script_generator import DialogueScriptGenerator
    _SCRIPT_AVAILABLE = True
except ImportError:
    DialogueScriptGenerator = None  # type: ignore
    _SCRIPT_AVAILABLE = False

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
