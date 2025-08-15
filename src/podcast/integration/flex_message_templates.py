# -*- coding: utf-8 -*-

"""
LINE Flex Message テンプレート生成クラス
ポッドキャスト通知用のリッチメッセージテンプレートを提供
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging


class FlexMessageTemplates:
    """
    LINE Flex Message テンプレート生成クラス
    
    ポッドキャスト配信通知用のリッチなメッセージテンプレートを生成
    """
    
    def __init__(self, logger: logging.Logger):
        """
        初期化
        
        Args:
            logger: ロガー
        """
        self.logger = logger
        
        # 色設定
        self.colors = {
            'primary': '#1DB446',     # LINE Green
            'secondary': '#404040',   # Dark Gray
            'accent': '#FF6B00',      # Orange
            'text_primary': '#333333',
            'text_secondary': '#666666',
            'background': '#F8F8F8'
        }
        
        # アイコン設定（絵文字）
        self.icons = {
            'podcast': '🎙️',
            'calendar': '📅',
            'highlight': '📊',
            'time': '⏱️',
            'size': '💾',
            'articles': '📰',
            'listen': '🎧',
            'rss': '📡',
            'play': '▶️',
            'download': '⬇️'
        }
    
    def create_podcast_notification_flex(self, episode_info: Dict[str, Any], articles: List[Dict[str, Any]], audio_url: Optional[str] = None, rss_url: Optional[str] = None) -> Dict[str, Any]:
        """
        ポッドキャスト通知用のFlex Messageを作成
        
        Args:
            episode_info: エピソード情報
            articles: 記事データ
            audio_url: 音声ファイルURL
            rss_url: RSSフィードURL
            
        Returns:
            Dict[str, Any]: Flex Message データ
        """
        try:
            # 基本情報を取得
            published_at = episode_info.get('published_at', datetime.now())
            file_size_mb = episode_info.get('file_size_mb', 0)
            article_count = episode_info.get('article_count', 0)
            
            # 日時フォーマット
            if isinstance(published_at, datetime):
                date_str = published_at.strftime('%Y年%m月%d日')
                time_str = published_at.strftime('%H:%M')
            else:
                date_str = datetime.now().strftime('%Y年%m月%d日')
                time_str = datetime.now().strftime('%H:%M')
            
            # 再生時間推定
            duration_min = int(file_size_mb * 1.5) if file_size_mb > 0 else 5
            
            # ハイライト作成
            highlights = self._create_article_highlights(articles, max_highlights=3)
            
            # Flex Message構築
            flex_message = {
                "type": "flex",
                "altText": f"{self.icons['podcast']} マーケットニュースポッドキャスト {date_str}",
                "contents": {
                    "type": "bubble",
                    "size": "kilo",
                    "header": self._create_header(date_str, time_str),
                    "body": self._create_body(highlights, duration_min, file_size_mb, article_count),
                    "footer": self._create_footer(audio_url, rss_url),
                    "styles": self._create_styles()
                }
            }
            
            self.logger.info("Flex Message テンプレート作成完了")
            return flex_message
            
        except Exception as e:
            self.logger.error(f"Flex Message 作成エラー: {e}")
            # フォールバック用のシンプルなメッセージ
            return self._create_simple_fallback_message(episode_info, articles)
    
    def _create_header(self, date_str: str, time_str: str) -> Dict[str, Any]:
        """
        ヘッダー部分を作成
        
        Args:
            date_str: 日付文字列
            time_str: 時刻文字列
            
        Returns:
            Dict[str, Any]: ヘッダー構造
        """
        return {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"{self.icons['podcast']} マーケットニュース",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#FFFFFF",
                            "flex": 1
                        },
                        {
                            "type": "text",
                            "text": "PODCAST",
                            "size": "xs",
                            "color": "#FFFFFF",
                            "align": "end",
                            "weight": "bold"
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"{self.icons['calendar']} {date_str}",
                            "size": "sm",
                            "color": "#FFFFFF",
                            "opacity": 0.8
                        },
                        {
                            "type": "text",
                            "text": time_str,
                            "size": "sm",
                            "color": "#FFFFFF",
                            "align": "end",
                            "opacity": 0.8
                        }
                    ]
                }
            ],
            "backgroundColor": self.colors['primary'],
            "paddingAll": "15px",
            "spacing": "sm"
        }
    
    def _create_body(self, highlights: List[str], duration_min: int, file_size_mb: float, article_count: int) -> Dict[str, Any]:
        """
        ボディ部分を作成
        
        Args:
            highlights: ハイライトリスト
            duration_min: 再生時間（分）
            file_size_mb: ファイルサイズ（MB）
            article_count: 記事数
            
        Returns:
            Dict[str, Any]: ボディ構造
        """
        contents = [
            {
                "type": "text",
                "text": f"{self.icons['highlight']} 本日のハイライト",
                "weight": "bold",
                "size": "md",
                "color": self.colors['text_primary'],
                "margin": "md"
            }
        ]
        
        # ハイライト項目を追加
        for highlight in highlights:
            contents.append({
                "type": "text",
                "text": f"• {highlight}",
                "size": "sm",
                "color": self.colors['text_secondary'],
                "wrap": True,
                "margin": "sm"
            })
        
        # 統計情報
        contents.extend([
            {
                "type": "separator",
                "margin": "lg"
            },
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{self.icons['time']} 再生時間",
                                "size": "xs",
                                "color": self.colors['text_secondary']
                            },
                            {
                                "type": "text",
                                "text": f"約{duration_min}分",
                                "weight": "bold",
                                "size": "sm",
                                "color": self.colors['text_primary']
                            }
                        ],
                        "flex": 1
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{self.icons['size']} サイズ",
                                "size": "xs",
                                "color": self.colors['text_secondary']
                            },
                            {
                                "type": "text",
                                "text": f"{file_size_mb:.1f}MB",
                                "weight": "bold",
                                "size": "sm",
                                "color": self.colors['text_primary']
                            }
                        ],
                        "flex": 1
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{self.icons['articles']} 記事数",
                                "size": "xs",
                                "color": self.colors['text_secondary']
                            },
                            {
                                "type": "text",
                                "text": f"{article_count}件",
                                "weight": "bold",
                                "size": "sm",
                                "color": self.colors['text_primary']
                            }
                        ],
                        "flex": 1
                    }
                ],
                "spacing": "sm",
                "margin": "md"
            }
        ])
        
        return {
            "type": "box",
            "layout": "vertical",
            "contents": contents,
            "paddingAll": "15px"
        }
    
    def _create_footer(self, audio_url: Optional[str], rss_url: Optional[str]) -> Dict[str, Any]:
        """
        フッター部分を作成
        
        Args:
            audio_url: 音声ファイルURL
            rss_url: RSSフィードURL
            
        Returns:
            Dict[str, Any]: フッター構造
        """
        buttons = []
        
        # 再生ボタン（音声URLがある場合）
        if audio_url:
            buttons.append({
                "type": "button",
                "action": {
                    "type": "uri",
                    "label": f"{self.icons['play']} 再生",
                    "uri": audio_url
                },
                "style": "primary",
                "color": self.colors['primary'],
                "flex": 2
            })
        
        # RSS購読ボタン（RSSURLがある場合）
        if rss_url:
            buttons.append({
                "type": "button",
                "action": {
                    "type": "uri",
                    "label": f"{self.icons['rss']} RSS",
                    "uri": rss_url
                },
                "style": "secondary",
                "flex": 1
            })
        
        # デフォルトボタンがない場合は情報ボタンを追加
        if not buttons:
            buttons.append({
                "type": "button",
                "action": {
                    "type": "postback",
                    "label": f"{self.icons['listen']} 詳細情報",
                    "data": "action=podcast_info"
                },
                "style": "secondary"
            })
        
        return {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "separator"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": buttons,
                    "spacing": "sm",
                    "margin": "md"
                }
            ],
            "paddingAll": "15px"
        }
    
    def _create_styles(self) -> Dict[str, Any]:
        """
        スタイル設定を作成
        
        Returns:
            Dict[str, Any]: スタイル構造
        """
        return {
            "header": {
                "backgroundColor": self.colors['primary']
            },
            "body": {
                "backgroundColor": "#FFFFFF"
            },
            "footer": {
                "backgroundColor": "#FFFFFF"
            }
        }
    
    def _create_article_highlights(self, articles: List[Dict[str, Any]], max_highlights: int = 3) -> List[str]:
        """
        記事のハイライトを作成
        
        Args:
            articles: 記事データ
            max_highlights: 最大ハイライト数
            
        Returns:
            List[str]: ハイライトリスト
        """
        highlights = []
        
        # センチメント別に記事を分類
        positive_articles = [a for a in articles if a.get('sentiment_label') == 'Positive']
        negative_articles = [a for a in articles if a.get('sentiment_label') == 'Negative']
        neutral_articles = [a for a in articles if a.get('sentiment_label') == 'Neutral']
        
        # 優先順位: Positive > Negative > Neutral
        priority_articles = positive_articles + negative_articles + neutral_articles
        
        for article in priority_articles[:max_highlights]:
            title = article.get('title', '')
            if title:
                # タイトルを短縮（45文字以内）
                if len(title) > 45:
                    title = title[:42] + "..."
                highlights.append(title)
        
        # ハイライトが少ない場合のフォールバック
        if not highlights:
            highlights = [
                "市場動向の詳細解説",
                "投資家向けの重要情報", 
                "経済ニュースの分析"
            ][:max_highlights]
        
        return highlights
    
    def _create_simple_fallback_message(self, episode_info: Dict[str, Any], articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        エラー時のフォールバック用シンプルメッセージ
        
        Args:
            episode_info: エピソード情報
            articles: 記事データ
            
        Returns:
            Dict[str, Any]: シンプルなテキストメッセージ
        """
        published_at = episode_info.get('published_at', datetime.now())
        if isinstance(published_at, datetime):
            date_str = published_at.strftime('%Y年%m月%d日 %H:%M')
        else:
            date_str = datetime.now().strftime('%Y年%m月%d日 %H:%M')
        
        message_text = f"{self.icons['podcast']} マーケットニュースポッドキャスト\n\n{self.icons['calendar']} {date_str} 配信\n\n{self.icons['listen']} 本日のマーケットニュースをAI音声でお届けします！"
        
        return {
            "type": "text",
            "text": message_text
        }
    
    def create_carousel_message(self, episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        複数エピソード用のカルーセルメッセージを作成
        
        Args:
            episodes: エピソードリスト
            
        Returns:
            Dict[str, Any]: Flex Carousel Message
        """
        try:
            bubbles = []
            
            for episode in episodes[:10]:  # 最大10件
                episode_info = episode.get('episode_info', {})
                articles = episode.get('articles', [])
                audio_url = episode.get('audio_url')
                
                # 各エピソード用のbubbleを作成
                bubble = self.create_podcast_notification_flex(episode_info, articles, audio_url)
                if bubble.get('contents'):
                    bubbles.append(bubble['contents'])
            
            if not bubbles:
                return self._create_simple_fallback_message({}, [])
            
            return {
                "type": "flex",
                "altText": f"{self.icons['podcast']} マーケットニュースポッドキャスト一覧",
                "contents": {
                    "type": "carousel",
                    "contents": bubbles
                }
            }
            
        except Exception as e:
            self.logger.error(f"カルーセルメッセージ作成エラー: {e}")
            return self._create_simple_fallback_message({}, [])