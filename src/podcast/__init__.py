# -*- coding: utf-8 -*-

"""
ポッドキャスト機能パッケージ
"""

from .script_generation.professional_dialogue_script_generator import ProfessionalDialogueScriptGenerator

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
    "ProfessionalDialogueScriptGenerator",
    "GeminiTTSEngine", 
    "AudioProcessor",
    "PodcastPublisher"
]
