# -*- coding: utf-8 -*-

"""
note投稿用マークダウンテンプレート
地域別のテンプレートとスタイルを提供
"""

from typing import Dict, List, Any
from datetime import datetime
from .region_filter import Region


class NoteTemplate:
    """note投稿用テンプレートクラス"""
    
    @staticmethod
    def get_base_template(region: Region, date: datetime) -> str:
        """
        地域別の基本テンプレートを取得
        
        Args:
            region: 地域
            date: 日付
            
        Returns:
            str: マークダウンテンプレート
        """
        region_configs = {
            Region.JAPAN: {
                'title': '🗾 今日の日本市場ニュース',
                'emoji': '🏯',
                'focus': '日経平均・東証・日本企業動向'
            },
            Region.USA: {
                'title': '🇺🇸 今日の米国市場ニュース', 
                'emoji': '🗽',
                'focus': 'S&P500・NASDAQ・FED政策'
            },
            Region.EUROPE: {
                'title': '🇪🇺 今日の欧州市場ニュース',
                'emoji': '🏛️',
                'focus': 'DAX・FTSE・ECB政策'
            }
        }
        
        config = region_configs.get(region, region_configs[Region.JAPAN])
        date_str = date.strftime('%Y年%m月%d日')
        
        return f"""{config['title']} ({date_str})

{config['emoji']} 今日の{region.value.upper()}市場をチェック！

こんにちは！今日も市場の動きをわかりやすくお届けします。
{config['focus']}を中心に、注目のニュースをまとめました。

{{market_data_table}}

{{market_overview}}

🔸 注目ニュース
━━━━━━━━━━━━━━━━━━━━━━━━

{{main_news}}

🔸 明日に向けて
━━━━━━━━━━━━━━━━━━━━━━━━

{{outlook}}

━━━━━━━━━━━━━━━━━━━━━━━━

この記事は最新の市場データとニュースを基に作成されています
投資判断は自己責任でお願いします 💼

{{timestamp}}
"""
    
    @staticmethod
    def format_market_overview(region: Region, articles: List[Dict[str, Any]], market_data: Dict[str, Any] = None) -> str:
        """
        市場概況セクションをフォーマット
        
        Args:
            region: 地域
            articles: 記事リスト
            market_data: 市場データ
            
        Returns:
            str: フォーマットされた市場概況
        """
        if not articles:
            return "本日は注目すべき市場動向はありませんでした。"
        
        # 地域別の市場指標
        region_indicators = {
            Region.JAPAN: "日経平均やTOPIXの動き",
            Region.USA: "S&P500やNASDAQの動き", 
            Region.EUROPE: "DAXやFTSE100の動き"
        }
        
        overview_template = f"""
{region_indicators.get(region, '市場の動き')}を中心に、今日は{"活発な動き" if len(articles) > 5 else "注目すべき動き"}が見られました。

主なトピック：
"""
        
        # 記事から主要トピックを抽出（最大3つ）
        topics = []
        for i, article in enumerate(articles[:3]):
            title = article.get('title', '')
            if len(title) > 50:
                title = title[:47] + "..."
            topics.append(f"• {title}")
        
        return overview_template + "\n".join(topics)
    
    @staticmethod
    def format_main_news(articles: List[Dict[str, Any]]) -> str:
        """
        主要ニュースセクションをフォーマット
        
        Args:
            articles: 記事リスト
            
        Returns:
            str: フォーマットされたニュース
        """
        if not articles:
            return "本日は特に大きなニュースはありませんでした。"
        
        news_sections = []
        
        for i, article in enumerate(articles[:5]):  # 最大5件
            title = article.get('title', '')
            summary = article.get('summary', '')
            source = article.get('source', '')
            
            # タイトルを適切な長さに調整
            if len(title) > 60:
                title = title[:57] + "..."
            
            # 要約を適切な長さに調整（200文字程度）
            if len(summary) > 200:
                summary = summary[:197] + "..."
            
            section = f"""
{i+1}. {title}

{summary}

出典: {source}
"""
            news_sections.append(section)
        
        return "\n".join(news_sections)
    
    @staticmethod
    def format_outlook(region: Region, articles: List[Dict[str, Any]]) -> str:
        """
        展望セクションをフォーマット
        
        Args:
            region: 地域
            articles: 記事リスト
            
        Returns:
            str: フォーマットされた展望
        """
        region_outlooks = {
            Region.JAPAN: {
                'focus': "日銀の政策動向や主要企業の決算発表",
                'emoji': "🏯"
            },
            Region.USA: {
                'focus': "FOMCの動向や主要テック企業の決算",
                'emoji': "🗽"
            },
            Region.EUROPE: {
                'focus': "ECBの政策やEU経済指標の発表", 
                'emoji': "🏛️"
            }
        }
        
        config = region_outlooks.get(region, region_outlooks[Region.JAPAN])
        
        if len(articles) == 0:
            return f"{config['emoji']} 明日も市場の動向に注目していきましょう！"
        
        # 記事内容から展望のヒントを抽出
        has_policy = any('政策' in article.get('title', '') + article.get('summary', '') for article in articles)
        has_earnings = any('決算' in article.get('title', '') + article.get('summary', '') for article in articles)
        
        outlook_parts = [f"{config['emoji']} 明日に向けての注目ポイント"]
        
        if has_policy:
            outlook_parts.append("• 金融政策の動向に引き続き注意が必要です")
        
        if has_earnings:
            outlook_parts.append("• 企業決算の発表が相次ぐため、個別株の動きにも注目です")
        
        outlook_parts.append(f"• {config['focus']}に特に注目しましょう")
        outlook_parts.append("\n市場は常に変化しています。最新情報をチェックして、良い投資判断を！ 📈")
        
        return "\n".join(outlook_parts)
    
    @staticmethod
    def generate_filename(region: Region, date: datetime) -> str:
        """
        ファイル名を生成
        
        Args:
            region: 地域
            date: 日付
            
        Returns:
            str: ファイル名
        """
        date_str = date.strftime('%Y-%m-%d')
        return f"{region.value}-{date_str}.md"
    
    @staticmethod
    def get_casual_phrases() -> List[str]:
        """
        カジュアルな表現のリストを取得
        
        Returns:
            List[str]: カジュアルフレーズ
        """
        return [
            "今日もお疲れ様でした！",
            "市場はなかなか面白い動きでしたね",
            "明日はどんな展開になるでしょうか？",
            "投資家の皆さん、今日はいかがでしたか？",
            "市場の動き、チェックできましたか？",
            "今日の注目ポイントを振り返ってみましょう",
            "明日も一緒に市場を見守りましょう！"
        ]