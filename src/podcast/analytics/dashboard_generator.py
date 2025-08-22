"""
パフォーマンスダッシュボード生成システム

このモジュールはWebベースの分析ダッシュボードを生成します。
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import base64
from io import BytesIO
from .analytics_engine import AnalyticsEngine
from .engagement_analyzer import EngagementAnalyzer
from .ab_test_manager import ABTestManager

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns

    plt.style.use("default")
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False


class DashboardGenerator:
    """分析ダッシュボード生成器"""

    def __init__(
        self,
        analytics_engine: Optional[AnalyticsEngine] = None,
        engagement_analyzer: Optional[EngagementAnalyzer] = None,
        ab_test_manager: Optional[ABTestManager] = None,
    ):
        self.analytics = analytics_engine or AnalyticsEngine()
        self.engagement = engagement_analyzer or EngagementAnalyzer(self.analytics)
        self.ab_tests = ab_test_manager or ABTestManager(self.analytics)
        self.logger = logging.getLogger(__name__)

    def generate_dashboard_data(self, days: int = 7) -> Dict[str, Any]:
        """ダッシュボードデータ生成"""
        try:
            dashboard_data = {
                "generated_at": datetime.datetime.now().isoformat(),
                "analysis_period": days,
                "overview": self._generate_overview_data(days),
                "performance_trends": self._generate_performance_trends(days),
                "engagement_analysis": self._generate_engagement_analysis(days),
                "ab_test_summary": self._generate_ab_test_summary(),
                "top_content": self._generate_top_content_data(days),
                "system_health": self._generate_system_health_data(),
            }

            if HAS_PLOTTING:
                dashboard_data["charts"] = self._generate_charts(dashboard_data, days)

            return dashboard_data

        except Exception as e:
            self.logger.error(f"ダッシュボードデータ生成エラー: {e}")
            return {"error": str(e)}

    def _generate_overview_data(self, days: int) -> Dict[str, Any]:
        """概要データ生成"""
        system_status = self.analytics.get_system_status()

        # パフォーマンストレンド取得
        trends = self.analytics.get_performance_trends(days)

        if trends:
            # 統計計算
            total_recipients = sum(t.total_recipients for t in trends)
            total_delivered = sum(t.successful_deliveries for t in trends)
            avg_ctr = sum(t.click_through_rate for t in trends) / len(trends)
            avg_engagement = sum(t.engagement_rate for t in trends) / len(trends)
            avg_conversion = sum(t.conversion_rate for t in trends) / len(trends)
        else:
            total_recipients = total_delivered = avg_ctr = avg_engagement = avg_conversion = 0

        return {
            "total_episodes": len(trends),
            "total_recipients": total_recipients,
            "total_delivered": total_delivered,
            "delivery_rate": (
                (total_delivered / total_recipients * 100) if total_recipients > 0 else 0
            ),
            "avg_click_through_rate": round(avg_ctr, 2),
            "avg_engagement_rate": round(avg_engagement, 2),
            "avg_conversion_rate": round(avg_conversion, 2),
            "today_stats": system_status.get("today", {}),
            "period_comparison": self._calculate_period_comparison(days),
        }

    def _generate_performance_trends(self, days: int) -> List[Dict[str, Any]]:
        """パフォーマンストレンド生成"""
        trends = self.analytics.get_performance_trends(days)

        return [
            {
                "date": trend.delivery_time.date().isoformat(),
                "episode_id": trend.episode_id,
                "recipients": trend.total_recipients,
                "delivered": trend.successful_deliveries,
                "click_through_rate": trend.click_through_rate,
                "engagement_rate": trend.engagement_rate,
                "conversion_rate": trend.conversion_rate,
                "read_time": trend.avg_read_time,
            }
            for trend in trends
        ]

    def _generate_engagement_analysis(self, days: int) -> Dict[str, Any]:
        """エンゲージメント分析生成"""
        # エンゲージメントトレンド
        engagement_trends = self.engagement.get_engagement_trends(days)

        # トップユーザー
        top_users = self.engagement.get_top_engaged_users(limit=5, days=days)

        # ヒートマップ
        heatmap_data = self.engagement.get_engagement_heatmap(days)

        return {
            "trends": [
                {
                    "date": trend.date.isoformat(),
                    "total_interactions": trend.total_interactions,
                    "unique_users": trend.unique_users,
                    "avg_engagement_score": trend.avg_engagement_score,
                    "top_content_types": trend.top_content_types,
                }
                for trend in engagement_trends
            ],
            "top_users": [
                {
                    "user_id": user.user_id,
                    "interactions": user.total_interactions,
                    "episodes": user.unique_episodes,
                    "engagement_score": user.engagement_score,
                    "avg_read_time": user.avg_read_time,
                    "subscribed": user.subscription_status,
                }
                for user in top_users
            ],
            "activity_heatmap": heatmap_data,
            "engagement_summary": self._calculate_engagement_summary(days),
        }

    def _generate_ab_test_summary(self) -> Dict[str, Any]:
        """A/Bテストサマリー生成"""
        active_tests = self.ab_tests.get_active_tests()

        test_results = []
        for test in active_tests[:3]:  # 最新3件
            result = self.ab_tests.get_test_results(test["test_id"])
            if result:
                test_results.append(result)

        return {
            "active_tests_count": len(active_tests),
            "recent_results": test_results,
            "active_tests": active_tests,
        }

    def _generate_top_content_data(self, days: int) -> Dict[str, Any]:
        """トップコンテンツデータ生成"""
        # パフォーマンストレンドからトップエピソード抽出
        trends = self.analytics.get_performance_trends(days)

        if not trends:
            return {"episodes": [], "content_types": []}

        # エンゲージメント率でソート
        top_episodes = sorted(trends, key=lambda x: x.engagement_rate, reverse=True)[:5]

        episodes_data = []
        for episode in top_episodes:
            engagement_summary = self.engagement.analyze_episode_engagement(episode.episode_id)
            episodes_data.append(
                {
                    "episode_id": episode.episode_id,
                    "delivery_time": episode.delivery_time.isoformat(),
                    "recipients": episode.total_recipients,
                    "engagement_rate": episode.engagement_rate,
                    "click_through_rate": episode.click_through_rate,
                    "views": engagement_summary.total_views if engagement_summary else 0,
                    "shares": engagement_summary.total_shares if engagement_summary else 0,
                }
            )

        return {"episodes": episodes_data, "content_types": self._analyze_content_types(days)}

    def _generate_system_health_data(self) -> Dict[str, Any]:
        """システムヘルス状態生成"""
        status = self.analytics.get_system_status()

        # 基本的なヘルスチェック
        health_score = 100
        issues = []

        # 配信失敗率チェック
        today_stats = status.get("today", {})
        failed_deliveries = today_stats.get("failed_deliveries", 0)
        total_deliveries = today_stats.get("total_deliveries", 1)
        failure_rate = (failed_deliveries / total_deliveries) * 100

        if failure_rate > 10:
            health_score -= 30
            issues.append("高い配信失敗率が検出されました")
        elif failure_rate > 5:
            health_score -= 15
            issues.append("配信失敗率が平均を上回っています")

        # データベースサイズチェック
        db_stats = status.get("database", {})
        total_events = db_stats.get("delivery_events", 0) + db_stats.get("engagement_events", 0)

        if total_events > 100000:
            issues.append(
                "データベースサイズが大きくなっています。クリーンアップを検討してください"
            )

        return {
            "overall_score": health_score,
            "status": (
                "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical"
            ),
            "issues": issues,
            "metrics": {
                "delivery_success_rate": round((1 - failure_rate / 100) * 100, 1),
                "total_events": total_events,
                "uptime_days": self._calculate_system_uptime(),
                "last_error": None,  # 実装要
            },
        }

    def _generate_charts(self, data: Dict[str, Any], days: int) -> Dict[str, str]:
        """チャート生成（Base64エンコード）"""
        if not HAS_PLOTTING:
            return {}

        charts = {}

        try:
            # パフォーマンストレンドチャート
            charts["performance_trend"] = self._create_performance_trend_chart(
                data["performance_trends"]
            )

            # エンゲージメント分析チャート
            charts["engagement_heatmap"] = self._create_engagement_heatmap_chart(
                data["engagement_analysis"]
            )

            # 配信成功率チャート
            charts["delivery_metrics"] = self._create_delivery_metrics_chart(
                data["performance_trends"]
            )

        except Exception as e:
            self.logger.error(f"チャート生成エラー: {e}")

        return charts

    def _create_performance_trend_chart(self, trends_data: List[Dict[str, Any]]) -> str:
        """パフォーマンストレンドチャート作成"""
        if not trends_data:
            return ""

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        dates = [datetime.datetime.fromisoformat(t["date"]) for t in trends_data]

        # エンゲージメント率とクリック率
        ax1.plot(
            dates,
            [t["engagement_rate"] for t in trends_data],
            "b-",
            label="エンゲージメント率",
            marker="o",
        )
        ax1.plot(
            dates,
            [t["click_through_rate"] for t in trends_data],
            "r-",
            label="クリック率",
            marker="s",
        )
        ax1.set_ylabel("率 (%)")
        ax1.set_title("エンゲージメント・クリック率トレンド")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 配信数と成功数
        ax2.bar(
            dates,
            [t["recipients"] for t in trends_data],
            alpha=0.7,
            label="配信数",
            color="skyblue",
        )
        ax2.bar(
            dates,
            [t["delivered"] for t in trends_data],
            alpha=0.7,
            label="成功配信数",
            color="lightgreen",
        )
        ax2.set_ylabel("件数")
        ax2.set_title("配信統計")
        ax2.legend()

        # X軸フォーマット
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _create_engagement_heatmap_chart(self, engagement_data: Dict[str, Any]) -> str:
        """エンゲージメントヒートマップチャート作成"""
        heatmap_data = engagement_data.get("activity_heatmap", {}).get("heatmap_data", {})

        if not heatmap_data:
            return ""

        # データ準備
        hours = list(range(24))
        days_of_week = ["日", "月", "火", "水", "木", "金", "土"]

        matrix = []
        for day in range(7):
            row = []
            for hour in hours:
                activity = heatmap_data.get(str(day), {}).get(str(hour), 0)
                row.append(activity)
            matrix.append(row)

        fig, ax = plt.subplots(figsize=(12, 6))

        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")

        # ラベル設定
        ax.set_xticks(range(24))
        ax.set_xticklabels([f"{h}:00" for h in hours])
        ax.set_yticks(range(7))
        ax.set_yticklabels(days_of_week)

        ax.set_xlabel("時間")
        ax.set_ylabel("曜日")
        ax.set_title("ユーザーアクティビティヒートマップ")

        # カラーバー
        plt.colorbar(im, ax=ax, label="アクティビティ数")

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _create_delivery_metrics_chart(self, trends_data: List[Dict[str, Any]]) -> str:
        """配信指標チャート作成"""
        if not trends_data:
            return ""

        fig, ax = plt.subplots(figsize=(10, 6))

        # データ準備
        dates = [datetime.datetime.fromisoformat(t["date"]) for t in trends_data]
        delivery_rates = [
            (t["delivered"] / t["recipients"]) * 100 if t["recipients"] > 0 else 0
            for t in trends_data
        ]

        # 配信成功率
        ax.plot(dates, delivery_rates, "g-", marker="o", linewidth=2, label="配信成功率")
        ax.axhline(y=95, color="r", linestyle="--", alpha=0.7, label="目標値 (95%)")

        ax.set_ylabel("配信成功率 (%)")
        ax.set_title("配信成功率トレンド")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(80, 100)

        # X軸フォーマット
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def _fig_to_base64(self, fig) -> str:
        """matplotlib図をBase64文字列に変換"""
        buffer = BytesIO()
        fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        buffer.seek(0)

        plot_data = buffer.getvalue()
        buffer.close()
        plt.close(fig)

        return base64.b64encode(plot_data).decode("utf-8")

    def _calculate_period_comparison(self, days: int) -> Dict[str, Any]:
        """期間比較計算"""
        current_trends = self.analytics.get_performance_trends(days)
        previous_trends = self.analytics.get_performance_trends(days * 2)

        if len(previous_trends) < days:
            return {}

        # 前期間データ
        previous_period = previous_trends[days:]

        if not current_trends or not previous_period:
            return {}

        # 平均値計算
        current_avg_engagement = sum(t.engagement_rate for t in current_trends) / len(
            current_trends
        )
        previous_avg_engagement = sum(t.engagement_rate for t in previous_period) / len(
            previous_period
        )

        current_avg_ctr = sum(t.click_through_rate for t in current_trends) / len(current_trends)
        previous_avg_ctr = sum(t.click_through_rate for t in previous_period) / len(previous_period)

        return {
            "engagement_rate_change": round(current_avg_engagement - previous_avg_engagement, 2),
            "click_through_rate_change": round(current_avg_ctr - previous_avg_ctr, 2),
            "engagement_rate_change_percent": (
                round(
                    ((current_avg_engagement - previous_avg_engagement) / previous_avg_engagement)
                    * 100,
                    1,
                )
                if previous_avg_engagement > 0
                else 0
            ),
            "click_through_rate_change_percent": (
                round(((current_avg_ctr - previous_avg_ctr) / previous_avg_ctr) * 100, 1)
                if previous_avg_ctr > 0
                else 0
            ),
        }

    def _calculate_engagement_summary(self, days: int) -> Dict[str, Any]:
        """エンゲージメントサマリー計算"""
        trends = self.engagement.get_engagement_trends(days)

        if not trends:
            return {}

        total_interactions = sum(t.total_interactions for t in trends)
        total_unique_users = sum(t.unique_users for t in trends)
        avg_score = sum(t.avg_engagement_score for t in trends) / len(trends)

        return {
            "total_interactions": total_interactions,
            "daily_avg_interactions": round(total_interactions / len(trends), 1),
            "total_unique_users": total_unique_users,
            "avg_engagement_score": round(avg_score, 2),
        }

    def _analyze_content_types(self, days: int) -> List[Dict[str, Any]]:
        """コンテンツタイプ分析"""
        # 簡易実装: エンゲージメントイベントタイプを分析
        trends = self.engagement.get_engagement_trends(days)

        content_type_stats = {}
        for trend in trends:
            for content_type in trend.top_content_types:
                if content_type not in content_type_stats:
                    content_type_stats[content_type] = {"count": 0, "interactions": 0}
                content_type_stats[content_type]["count"] += 1
                content_type_stats[content_type]["interactions"] += trend.total_interactions

        return [
            {
                "type": content_type,
                "count": stats["count"],
                "total_interactions": stats["interactions"],
                "avg_interactions": round(stats["interactions"] / stats["count"], 1),
            }
            for content_type, stats in sorted(
                content_type_stats.items(), key=lambda x: x[1]["interactions"], reverse=True
            )
        ]

    def _calculate_system_uptime(self) -> int:
        """システム稼働日数計算（簡易版）"""
        # 実装簡略化: データベース最古のレコードから計算
        try:
            import sqlite3

            with sqlite3.connect(self.analytics.db_path) as conn:
                oldest_record = conn.execute(
                    """
                    SELECT MIN(created_at) FROM (
                        SELECT created_at FROM delivery_events
                        UNION ALL
                        SELECT created_at FROM engagement_events
                    )
                """
                ).fetchone()[0]

                if oldest_record:
                    oldest_date = datetime.datetime.fromisoformat(oldest_record)
                    uptime = (datetime.datetime.now() - oldest_date).days
                    return max(0, uptime)
        except Exception:
            pass

        return 0

    def save_dashboard_html(self, data: Dict[str, Any], output_path: str):
        """ダッシュボードHTML保存"""
        html_content = self._generate_dashboard_html(data)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.logger.info(f"ダッシュボードHTML保存: {output_path}")
        except Exception as e:
            self.logger.error(f"HTML保存エラー: {e}")

    def _generate_dashboard_html(self, data: Dict[str, Any]) -> str:
        """ダッシュボードHTML生成"""
        return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ポッドキャスト配信分析ダッシュボード</title>
    <style>
        body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ color: #7f8c8d; margin-top: 5px; }}
        .chart-container {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .chart-img {{ max-width: 100%; height: auto; }}
        .table {{ width: 100%; border-collapse: collapse; }}
        .table th, .table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        .table th {{ background-color: #f8f9fa; }}
        .health-indicator {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }}
        .health-healthy {{ background-color: #28a745; }}
        .health-warning {{ background-color: #ffc107; }}
        .health-critical {{ background-color: #dc3545; }}
        .timestamp {{ text-align: center; color: #6c757d; margin-top: 20px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ポッドキャスト配信分析ダッシュボード</h1>
            <p>分析期間: {data.get('analysis_period', 7)}日間</p>
        </div>
        
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{data.get('overview', {}).get('total_episodes', 0)}</div>
                <div class="metric-label">配信エピソード数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{data.get('overview', {}).get('total_recipients', 0):,}</div>
                <div class="metric-label">総配信数</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{data.get('overview', {}).get('delivery_rate', 0):.1f}%</div>
                <div class="metric-label">配信成功率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{data.get('overview', {}).get('avg_engagement_rate', 0):.1f}%</div>
                <div class="metric-label">平均エンゲージメント率</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3>パフォーマンストレンド</h3>
            {self._render_chart(data.get('charts', {}).get('performance_trend', ''))}
        </div>
        
        <div class="chart-container">
            <h3>ユーザーアクティビティヒートマップ</h3>
            {self._render_chart(data.get('charts', {}).get('engagement_heatmap', ''))}
        </div>
        
        <div class="chart-container">
            <h3>トップエピソード</h3>
            <table class="table">
                <thead>
                    <tr>
                        <th>エピソードID</th>
                        <th>配信時刻</th>
                        <th>配信数</th>
                        <th>エンゲージメント率</th>
                        <th>クリック率</th>
                    </tr>
                </thead>
                <tbody>
                    {self._render_episode_table(data.get('top_content', {}).get('episodes', []))}
                </tbody>
            </table>
        </div>
        
        <div class="chart-container">
            <h3>システムヘルス</h3>
            <p>
                <span class="health-indicator health-{data.get('system_health', {}).get('status', 'warning')}"></span>
                ステータス: {data.get('system_health', {}).get('status', 'unknown').title()}
                (スコア: {data.get('system_health', {}).get('overall_score', 0)}/100)
            </p>
            {self._render_health_issues(data.get('system_health', {}).get('issues', []))}
        </div>
        
        <div class="timestamp">
            最終更新: {data.get('generated_at', '')}
        </div>
    </div>
</body>
</html>
        """

    def _render_chart(self, chart_base64: str) -> str:
        """チャート画像レンダリング"""
        if chart_base64:
            return f'<img src="data:image/png;base64,{chart_base64}" class="chart-img" alt="Chart">'
        return "<p>チャートデータがありません</p>"

    def _render_episode_table(self, episodes: List[Dict[str, Any]]) -> str:
        """エピソードテーブルレンダリング"""
        if not episodes:
            return '<tr><td colspan="5">データがありません</td></tr>'

        rows = []
        for episode in episodes[:10]:  # トップ10
            rows.append(
                f"""
            <tr>
                <td>{episode.get('episode_id', '')[:12]}...</td>
                <td>{episode.get('delivery_time', '')[:16]}</td>
                <td>{episode.get('recipients', 0):,}</td>
                <td>{episode.get('engagement_rate', 0):.1f}%</td>
                <td>{episode.get('click_through_rate', 0):.1f}%</td>
            </tr>
            """
            )

        return "".join(rows)

    def _render_health_issues(self, issues: List[str]) -> str:
        """ヘルスイシューレンダリング"""
        if not issues:
            return "<p>問題は検出されていません。</p>"

        issue_list = "".join(f"<li>{issue}</li>" for issue in issues)
        return f"<ul>{issue_list}</ul>"
