"""
note用Markdownレンダラ
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader, Template

from ..personalization.topic_selector import Topic


class MarkdownRenderer:
    """note用Markdown生成器"""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Args:
            template_dir: テンプレートディレクトリのパス
        """
        if template_dir is None:
            # プロジェクトルートのassetsディレクトリを使用
            project_root = Path(__file__).parent.parent.parent
            template_dir = project_root / "assets" / "templates" / "note"
        
        self.template_dir = Path(template_dir)
        
        # テンプレート環境を設定
        if self.template_dir.exists():
            self.env = Environment(loader=FileSystemLoader(str(self.template_dir)))
        else:
            # ディレクトリが存在しない場合はダミー環境
            self.env = None
    
    def render(
        self,
        date: datetime,
        topics: List[Topic],
        integrated_summary: str,
        output_dir: str,
        title: Optional[str] = None,
        market_overview: Optional[str] = None
    ) -> Path:
        """
        note用Markdownを生成
        
        Args:
            date: 日付
            topics: 選定されたトピック
            integrated_summary: 統合要約
            output_dir: 出力ディレクトリ
            title: カスタムタイトル
            market_overview: 市場概況
            
        Returns:
            生成されたファイルのパス
        """
        # 出力ディレクトリを作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # ファイル名を生成
        filename = f"{date.strftime('%Y-%m-%d')}.md"
        file_path = output_path / filename
        
        # テンプレート変数を準備
        template_vars = {
            'date': date,
            'date_str': date.strftime('%Y年%m月%d日'),
            'date_iso': date.strftime('%Y-%m-%d'),
            'title': title or f"市場ニュース {date.strftime('%Y/%m/%d')}",
            'topics': topics,
            'integrated_summary': integrated_summary,
            'market_overview': market_overview or integrated_summary,
            'social_image_path': f"../social/{date.strftime('%Y%m%d')}/news_01_16x9.png",
            'charts_dir': f"../charts/{date.strftime('%Y%m%d')}/",
        }
        
        # テンプレートを使用してレンダリング
        if self.env:
            try:
                template = self.env.get_template('post.md.j2')
                content = template.render(**template_vars)
            except Exception:
                # テンプレートが見つからない場合はデフォルトを使用
                content = self._render_default_template(**template_vars)
        else:
            content = self._render_default_template(**template_vars)
        
        # ファイルに書き込み
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def _render_default_template(self, **kwargs) -> str:
        """デフォルトテンプレートでレンダリング"""
        date_str = kwargs['date_str']
        title = kwargs['title']
        topics = kwargs['topics']
        integrated_summary = kwargs['integrated_summary']
        market_overview = kwargs['market_overview']
        social_image_path = kwargs['social_image_path']
        
        # トピックセクションを生成
        topics_section = ""
        if topics:
            topics_section = "## 今日の3つのポイント\n\n"
            for i, topic in enumerate(topics, 1):
                topics_section += f"### {i}. {topic.headline}\n\n"
                if topic.blurb:
                    topics_section += f"{topic.blurb}\n\n"
                topics_section += f"**出典**: [{topic.source}]({topic.url})\n\n"
        
        # Markdownを生成
        content = f"""# {title}

*{date_str}*

## リード

本日の市場では、以下の重要な動きが見られました。

{topics_section}

## 市場概況

{market_overview}

## 注目トピック詳細

"""
        
        # 各トピックの詳細を追加
        for i, topic in enumerate(topics, 1):
            content += f"### {topic.headline}\n\n"
            content += f"{topic.blurb}\n\n"
            content += f"- **カテゴリ**: {topic.category or 'N/A'}\n"
            content += f"- **地域**: {topic.region or 'N/A'}\n"
            content += f"- **出典**: [{topic.source}]({topic.url})\n"
            content += f"- **公開時刻**: {topic.published_jst.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        content += f"""
## 図版

![市場ニュース画像]({social_image_path})

*本日の市場動向をまとめた画像*

## まとめ

本日の市場では、{len(topics)}つの重要な動きが確認されました。投資家の皆様におかれましては、これらの情報を参考に慎重な投資判断を行ってください。

---

*このレポートは自動生成されたものです。投資判断は自己責任でお願いします。*
"""
        
        return content