# -*- coding: utf-8 -*-

def create_html_file(articles: list, output_path: str = "index.html"):
    """
    要約された記事リストからHTMLファイルを生成します。
    
    Args:
        articles (list): 要約済みの記事データを含む辞書のリスト。
                         各辞書は 'title', 'url', 'published_jst', 'summary' キーを持つことを想定。
        output_path (str): 生成するHTMLファイルのパス。
    """
    html_content = f"""
<!DOCTYPE html>
<html lang="ja" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>本日のマーケットニュース要約</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2.0.6/css/pico.min.css">
    <style>
        body {{ font-family: 'Noto Sans JP', sans-serif; }}
        .container {{ max-width: 960px; margin: 2rem auto; padding: 1rem; }}
        article {{ margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid var(--pico-form-element-border-color); }}
        article:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
        h2 {{ margin-bottom: 0.5rem; }}
        small {{ color: var(--pico-secondary-text-color); display: block; margin-bottom: 0.5rem; }}
        p {{ margin-top: 0.5rem; }}
        .source {{ font-weight: bold; color: var(--pico-primary); }}
    </style>
</head>
<body>
    <main class="container">
        <hgroup>
            <h1>本日のマーケットニュース要約</h1>
            <p>AIが主要ニュースサイトから収集・要約した最新情報</p>
        </hgroup>
        <section>
"""

    if not articles:
        html_content += "            <p>本日、新しいニュース記事は見つかりませんでした。</p>\n"
    else:
        for article in articles:
            title = article.get('title', 'タイトル不明')
            url = article.get('url', '#')
            published_jst = article.get('published_jst', '日時不明').strftime('%Y-%m-%d %H:%M') if hasattr(article.get('published_jst'), 'strftime') else article.get('published_jst', '日時不明')
            summary = article.get('summary', '要約なし')
            source = article.get('category', '不明なソース').replace('category', '') # ロイターのカテゴリ名から'category'を削除

            html_content += f"""
            <article>
                <h2><a href="{url}" target="_blank">{title}</a></h2>
                <small><span class="source">[{source}]</span> {published_jst}</small>
                <p>{summary}</p>
            </article>
"""

    # 最終更新日時を安全に取得
    last_updated = "N/A"
    if articles:
        first_article_time = articles[0].get('published_jst')
        if hasattr(first_article_time, 'strftime'):
            last_updated = first_article_time.strftime('%Y-%m-%d %H:%M')

    html_content += f"""
        </section>
        <footer>
            <p><small>最終更新: {last_updated}</small></p>
            <p><small>Powered by Gemini AI & Python Scrapers</small></p>
        </footer>
    </main>
</body>
</html>
"""

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"HTMLファイル '{output_path}' を生成しました。")
    except IOError as e:
        print(f"HTMLファイルの書き込み中にエラーが発生しました: {e}")

if __name__ == '__main__':
    # テスト用のコード
    from datetime import datetime
    import pytz

    jst = pytz.timezone('Asia/Tokyo')

    test_articles = [
        {
            'title': 'テスト記事1: FRB、政策金利を据え置き', 
            'url': 'https://example.com/article1',
            'published_jst': datetime(2025, 6, 26, 10, 30, tzinfo=jst),
            'summary': '米連邦準備制度理事会（FRB）は、市場の予想通り政策金利を据え置いた。パウエル議長は今後の金融政策について「データ次第」と述べ、利下げ時期の明言を避けた。市場では9月利下げ開始の見方が強いが、FRBはインフレを警戒している。',
            'category': '経済category'
        },
        {
            'title': 'テスト記事2: テック企業の決算発表', 
            'url': 'https://example.com/article2',
            'published_jst': datetime(2025, 6, 26, 11, 0, tzinfo=jst),
            'summary': '主要テック企業が好調な四半期決算を発表し、株価が上昇した。特にクラウド部門の成長が顕著で、今後の市場を牽引する見込み。AI関連投資も活発化している。',
            'category': 'テクノロジーcategory'
        }
    ]

    create_html_file(test_articles)
    create_html_file([]) # 記事がない場合のテスト
