"""ポッドキャスト配信モジュール

パッケージ配下の新実装に加え、既存の `src/podcast/publisher.py`
で提供されている互換API（テストで利用）もエクスポートする。
"""

import importlib.util
from pathlib import Path

# 既存の互換APIを取り込み（ユニットテストが依存）
_legacy_module_path = Path(__file__).resolve().parent.parent / "publisher.py"
_legacy_spec = importlib.util.spec_from_file_location(
    "src.podcast._legacy_publisher", _legacy_module_path
)
legacy_publisher = importlib.util.module_from_spec(_legacy_spec)  # type: ignore[arg-type]
if _legacy_spec and _legacy_spec.loader:
    _legacy_spec.loader.exec_module(legacy_publisher)  # type: ignore[union-attr]
else:  # pragma: no cover - ローダーが取得できない場合のフェイルセーフ
    raise ImportError("legacy podcast publisher module could not be loaded")

# 新実装（social配信など）も引き続き公開
from .podcast_publisher import PodcastPublisher
from .rss_generator import RSSGenerator as AdvancedRSSGenerator
from .line_broadcaster import LINEBroadcaster as SocialLINEBroadcaster

# 互換レイヤーとして旧APIをデフォルトエクスポート
RSSGenerator = legacy_publisher.RSSGenerator
LINEBroadcaster = legacy_publisher.LINEBroadcaster
PodcastEpisode = legacy_publisher.PodcastEpisode
PublishResult = legacy_publisher.PublishResult
RSSPublishingError = legacy_publisher.RSSPublishingError
GitHubPagesError = legacy_publisher.GitHubPagesError
LINEBroadcastingError = legacy_publisher.LINEBroadcastingError
LINEAPIError = legacy_publisher.LINEAPIError
FEEDGEN_AVAILABLE = legacy_publisher.FEEDGEN_AVAILABLE
REQUESTS_AVAILABLE = legacy_publisher.REQUESTS_AVAILABLE

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
    "REQUESTS_AVAILABLE",
    # 追加の新実装を参照したい場合用
    "AdvancedRSSGenerator",
    "SocialLINEBroadcaster",
]
