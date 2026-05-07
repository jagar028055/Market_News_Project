"""ポッドキャスト配信モジュール

このパッケージは RSS/LINE 配信機能を提供します。
テストとの後方互換性のため、下記のクラスをこのパッケージから直接エクスポートします。
"""

import os as _os
import importlib.util as _util
import sys as _sys

# ─── 例外クラスは rss_generator から一元インポート ─────────────────────────
try:
    from .rss_generator import (
        RSSGenerator,
        RSSPublishingError,
        GitHubPagesError,
        FEEDGEN_AVAILABLE,
        FeedGenerator,
    )
    _RSS_AVAILABLE = True
except Exception:
    RSSGenerator = None          # type: ignore
    RSSPublishingError = None    # type: ignore
    GitHubPagesError = None      # type: ignore
    FEEDGEN_AVAILABLE = False
    FeedGenerator = None         # type: ignore
    _RSS_AVAILABLE = False

# ─── PodcastEpisode / PublishResult / LINE 例外クラスは publisher.py から取得 ─
# publisher.py は src/podcast/publisher.py（このパッケージと同名の旧フラットモジュール）
_legacy_mod = None
try:
    # __file__ が .pyc になっていても対応できるよう os.path ベースで計算
    _pkg_dir = _os.path.dirname(_os.path.abspath(__file__))  # .../src/podcast/publisher/
    _legacy_path = _os.path.join(_os.path.dirname(_pkg_dir), "publisher.py")  # .../src/podcast/publisher.py
    if _os.path.exists(_legacy_path):
        _spec = _util.spec_from_file_location("_podcast_publisher_legacy", _legacy_path)
        if _spec and _spec.loader:
            _legacy_mod = _util.module_from_spec(_spec)
            _spec.loader.exec_module(_legacy_mod)  # type: ignore
except Exception:
    _legacy_mod = None

if _legacy_mod is not None:
    PodcastEpisode = getattr(_legacy_mod, "PodcastEpisode", None)
    PublishResult = getattr(_legacy_mod, "PublishResult", None)
    LINEBroadcastingError = getattr(_legacy_mod, "LINEBroadcastingError", None)
    LINEAPIError = getattr(_legacy_mod, "LINEAPIError", None)
    _LEGACY_AVAILABLE = True
    # legacy の RSSPublishingError / GitHubPagesError は使わない
    # (rss_generator.py のものを正として使う)
else:
    PodcastEpisode = None         # type: ignore
    PublishResult = None          # type: ignore
    LINEBroadcastingError = None  # type: ignore
    LINEAPIError = None           # type: ignore
    _LEGACY_AVAILABLE = False

# ─── 他のサブモジュール ──────────────────────────────────────────────────────
try:
    from .podcast_publisher import PodcastPublisher
    _PODCAST_PUBLISHER_AVAILABLE = True
except Exception:
    PodcastPublisher = None       # type: ignore
    _PODCAST_PUBLISHER_AVAILABLE = False

try:
    from .line_broadcaster import LINEBroadcaster
    _LINE_BROADCASTER_AVAILABLE = True
except Exception:
    LINEBroadcaster = None        # type: ignore
    _LINE_BROADCASTER_AVAILABLE = False

__all__ = [
    "PodcastPublisher",
    "RSSGenerator",
    "LINEBroadcaster",
    "PodcastEpisode",
    "PublishResult",
    "RSSPublishingError",
    "GitHubPagesError",
    "LINEBroadcastingError",
    "LINEAPIError",
    "FEEDGEN_AVAILABLE",
    "FeedGenerator",
]
