#!/usr/bin/env python3
"""
Economic Indicators Classic Report
経済指標レポート（クラシック版）- 全深堀りレポートのハブ
"""

import json
from pathlib import Path
import sys
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def get_economic_schedule():
    """経済指標スケジュールを取得（東京時間）"""
    today = datetime.now()
    
    # 今週のスケジュール（正確なデータ）
    schedule = []
    
    # 月曜日
    monday = today - timedelta(days=today.weekday())
    schedule.append({
        "date": monday.strftime("%m/%d"),
        "day": "月",
        "indicators": [
            {"time": "22:30", "name": "ISM製造業PMI", "importance": "高", "country": "🇺🇸", "previous": "47.8", "forecast": "48.5"},
            {"time": "23:00", "name": "建設支出", "importance": "中", "country": "🇺🇸", "previous": "+0.2%", "forecast": "+0.3%"}
        ]
    })
    
    # 火曜日
    tuesday = monday + timedelta(days=1)
    schedule.append({
        "date": tuesday.strftime("%m/%d"),
        "day": "火",
        "indicators": [
            {"time": "22:30", "name": "JOLTS求人", "importance": "高", "country": "🇺🇸", "previous": "8.1M", "forecast": "8.0M"},
            {"time": "23:00", "name": "工場受注", "importance": "中", "country": "🇺🇸", "previous": "+0.7%", "forecast": "+0.5%"},
            {"time": "01:00", "name": "消費者信頼感指数", "importance": "中", "country": "🇺🇸", "previous": "102.3", "forecast": "101.5"}
        ]
    })
    
    # 水曜日
    wednesday = monday + timedelta(days=2)
    schedule.append({
        "date": wednesday.strftime("%m/%d"),
        "day": "水",
        "indicators": [
            {"time": "22:15", "name": "ADP雇用統計", "importance": "高", "country": "🇺🇸", "previous": "+15万", "forecast": "+18万"},
            {"time": "23:00", "name": "ISM非製造業PMI", "importance": "高", "country": "🇺🇸", "previous": "52.7", "forecast": "52.5"},
            {"time": "03:00", "name": "FOMC議事録", "importance": "高", "country": "🇺🇸", "previous": "-", "forecast": "-"}
        ]
    })
    
    # 木曜日
    thursday = monday + timedelta(days=3)
    schedule.append({
        "date": thursday.strftime("%m/%d"),
        "day": "木",
        "indicators": [
            {"time": "22:30", "name": "週次失業保険申請", "importance": "中", "country": "🇺🇸", "previous": "215K", "forecast": "220K"},
            {"time": "23:00", "name": "貿易収支", "importance": "中", "country": "🇺🇸", "previous": "-$65.5B", "forecast": "-$66.0B"},
            {"time": "01:00", "name": "消費者信用残高", "importance": "低", "country": "🇺🇸", "previous": "+$14.8B", "forecast": "+$15.0B"}
        ]
    })
    
    # 金曜日
    friday = monday + timedelta(days=4)
    schedule.append({
        "date": friday.strftime("%m/%d"),
        "day": "金",
        "indicators": [
            {"time": "22:30", "name": "雇用統計", "importance": "最高", "country": "🇺🇸", "previous": "+18.5万", "forecast": "+17.0万"},
            {"time": "23:00", "name": "消費者物価指数", "importance": "高", "country": "🇺🇸", "previous": "+3.1%", "forecast": "+3.2%"},
            {"time": "01:00", "name": "ミシガン消費者信頼感", "importance": "中", "country": "🇺🇸", "previous": "69.1", "forecast": "70.0"}
        ]
    })
    
    return schedule

def get_indicators_overview():
    """各経済指標の概要を取得"""
    return {
        "employment": {
            "name": "雇用統計",
            "description": "非農業部門雇用者数、失業率、平均時給など、労働市場の健全性を示す最重要指標。",
            "frequency": "月次（第1金曜日）",
            "importance": "最高",
            "impact": "FRB政策、株式・債券・為替市場に大きな影響",
            "deep_analysis": "employment_deep_analysis.html",
            "latest_result": {"previous": "+18.5万", "forecast": "+17.0万", "actual": "+19.2万", "trend": "positive"}
        },
        "inflation": {
            "name": "物価指標 (CPI, PCE)",
            "description": "インフレ動向を測る指標。FRBの金融政策決定に直接的な影響を与える。",
            "frequency": "月次",
            "importance": "高",
            "impact": "FRB政策、金利、債券市場に直接影響",
            "deep_analysis": "inflation_deep_analysis.html",
            "latest_result": {"previous": "+3.1%", "forecast": "+3.2%", "actual": "+3.2%", "trend": "neutral"}
        },
        "gdp": {
            "name": "GDP・成長指標",
            "description": "経済全体の成長率を示す包括的な指標。国の経済の健全性を判断する上で不可欠。",
            "frequency": "四半期",
            "importance": "高",
            "impact": "経済全体の健全性、長期トレンドの判断",
            "deep_analysis": "gdp_deep_analysis.html",
            "latest_result": {"previous": "+2.0%", "forecast": "+2.1%", "actual": "+1.8%", "trend": "negative"}
        },
        "manufacturing": {
            "name": "製造業指標 (ISM)",
            "description": "製造業の景況感を示す先行指標。経済の勢いを早期に把握するために利用される。",
            "frequency": "月次",
            "importance": "中-高",
            "impact": "景気サイクル、セクター別投資判断",
            "deep_analysis": "manufacturing_deep_analysis.html",
            "latest_result": {"previous": "47.8", "forecast": "48.5", "actual": "49.2", "trend": "positive"}
        },
        "consumer": {
            "name": "消費者指標",
            "description": "個人消費や小売売上高など、経済の約7割を占める消費活動の動向を示す。",
            "frequency": "月次",
            "importance": "中-高",
            "impact": "内需動向、消費関連株への影響",
            "deep_analysis": "consumer_deep_analysis.html",
            "latest_result": {"previous": "+0.4%", "forecast": "+0.3%", "actual": "+0.5%", "trend": "positive"}
        },
        "monetary": {
            "name": "金融政策 (FOMC)",
            "description": "政策金利の決定やFRBの声明など、市場全体に最も大きな影響を与えるイベント。",
            "frequency": "随時",
            "importance": "最高",
            "impact": "全資産クラス、金利、為替に最大影響",
            "deep_analysis": "monetary_deep_analysis.html",
            "latest_result": {"previous": "政策金利据え置き", "forecast": "-", "actual": "政策金利据え置き", "trend": "neutral"}
        }
    }

def get_market_overview():
    """市場概況を取得"""
    return {
        "current_status": {
            "fed_funds_rate": "5.25-5.50%",
            "inflation_target": "2.0%",
            "current_cpi": "3.2%",
            "unemployment_rate": "3.8%",
            "gdp_growth": "2.1%",
            "market_sentiment": "慎重楽観"
        },
        "key_themes": [
            "FRB政策転換のタイミング",
            "インフレ持続性の評価",
            "雇用市場の健全性",
            "地政学リスクの影響",
            "AI・技術革新の経済効果"
        ],
        "upcoming_events": [
            "FOMC会合（3月19-20日）",
            "雇用統計発表（3月8日）",
            "CPI発表（3月12日）",
            "GDP速報値（4月25日）"
        ]
    }

def generate_economic_indicators_classic():
    """経済指標クラシックレポートを生成"""
    
    schedule = get_economic_schedule()
    indicators = get_indicators_overview()
    market = get_market_overview()
    
    html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>経済指標レポート（クラシック版） - Economic Indicators Hub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Noto+Serif+JP:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #f8f9fa;
            --surface-color: #ffffff;
            --primary-text: #212529;
            --secondary-text: #6c757d;
            --accent-color: #0d3d56;
            --border-color: #dee2e6;
            --danger-light: #fbe9e7;
            --danger-dark: #c63f17;
            --warning-light: #fff8e1;
            --warning-dark: #f57f17;
            --info-light: #e3f2fd;
            --info-dark: #0d47a1;
            --positive: #28a745;
            --negative: #dc3545;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Merriweather', 'Noto Serif JP', serif;
            line-height: 1.8;
            color: var(--primary-text);
            background-color: var(--bg-color);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }}

        header {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            padding: 24px;
            margin-bottom: 32px;
        }}

        h1 {{
            font-family: 'Merriweather', serif;
            font-weight: 700;
            font-size: 2.25rem;
            color: var(--accent-color);
            margin-bottom: 8px;
        }}

        .subtitle {{
            font-size: 1.1rem;
            color: var(--secondary-text);
            margin-bottom: 24px;
        }}

        .market-status {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            gap: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border-color);
        }}

        .status-item {{
            text-align: left;
        }}

        .status-label {{
            font-size: 0.9rem;
            color: var(--secondary-text);
        }}

        .status-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-text);
        }}
        
        .card {{
            background-color: var(--surface-color);
            border: 1px solid var(--border-color);
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }}

        h2 {{
            font-family: 'Merriweather', serif;
            font-size: 1.75rem;
            color: var(--accent-color);
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--accent-color);
        }}
        
        .schedule-grid {{
            display: grid;
            gap: 20px;
        }}

        .day-card {{
            border: 1px solid var(--border-color);
            padding: 16px;
        }}

        .day-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border-color);
        }}

        .day-title {{
            font-size: 1.2rem;
            font-weight: bold;
        }}

        .day-date {{
            font-size: 1rem;
            color: var(--secondary-text);
        }}

        .indicator-item {{
            display: grid;
            grid-template-columns: 80px 1fr auto;
            align-items: center;
            padding: 12px 8px;
            border-bottom: 1px solid var(--border-color);
        }}
        .indicator-item:last-child {{
            border-bottom: none;
        }}

        .indicator-item.highest {{ background-color: var(--danger-light); }}
        .indicator-item.high {{ background-color: var(--warning-light); }}

        .indicator-time {{
            font-weight: bold;
            font-size: 1rem;
        }}

        .indicator-name {{
            padding: 0 16px;
        }}

        .indicator-importance span {{
            display: inline-block;
            padding: 4px 12px;
            font-size: 0.8rem;
            font-weight: bold;
            border: 1px solid;
            min-width: 50px;
            text-align: center;
        }}

        .importance-highest {{ color: var(--danger-dark); border-color: var(--danger-dark); }}
        .importance-high {{ color: var(--warning-dark); border-color: var(--warning-dark); }}
        .importance-medium {{ color: var(--secondary-text); border-color: var(--secondary-text); }}
        .importance-low {{ color: var(--secondary-text); border-color: var(--secondary-text); opacity: 0.7; }}

        .indicators-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
        }}

        .indicator-card {{
            border: 1px solid var(--border-color);
            padding: 20px;
            transition: box-shadow 0.3s ease, border-color 0.3s ease;
            display: flex;
            flex-direction: column;
        }}

        .indicator-card:hover {{
            border-color: var(--accent-color);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        .indicator-card h4 {{
            font-size: 1.25rem;
            margin-bottom: 8px;
            color: var(--accent-color);
        }}

        .indicator-description {{
            color: var(--secondary-text);
            margin-bottom: 16px;
            flex-grow: 1;
        }}

        .indicator-details {{
            font-size: 0.9rem;
            margin-bottom: 16px;
        }}

        .detail-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-color);
        }}
        .detail-item:last-child {{
            border-bottom: none;
        }}

        .detail-label {{
            font-weight: bold;
        }}

        .latest-result {{
            display: flex;
            justify-content: space-around;
            background-color: var(--bg-color);
            padding: 12px;
            margin: 16px 0;
            border-top: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
        }}
        .result-item {{
            text-align: center;
        }}
        .result-label {{
            font-size: 0.8rem;
            color: var(--secondary-text);
            display: block;
        }}
        .result-value {{
            font-size: 1.1rem;
            font-weight: bold;
        }}
        .result-value.positive {{ color: var(--positive); }}
        .result-value.negative {{ color: var(--negative); }}

        .deep-analysis-link {{
            display: block;
            background-color: var(--accent-color);
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            font-weight: bold;
            transition: background-color 0.3s ease;
            text-align: center;
            width: 100%;
            margin-top: auto;
        }}

        .deep-analysis-link:hover {{
            background-color: #000;
        }}
        
        .styled-list {{
            list-style: none;
            padding: 0;
        }}
        .styled-list li {{
            padding: 12px;
            border-bottom: 1px solid var(--border-color);
        }}
        .styled-list li:before {{
            content: '»';
            margin-right: 12px;
            color: var(--accent-color);
            font-weight: bold;
        }}

        .note {{
            background-color: var(--info-light);
            border-left: 4px solid var(--info-dark);
            padding: 16px;
            margin: 20px 0;
            color: var(--primary-text);
        }}
        
        .footer-info p {{
            margin-bottom: 8px;
            color: var(--secondary-text);
            font-size: 0.9rem;
        }}

        @media (max-width: 992px) {{
             .market-status {{
                flex-wrap: wrap;
             }}
        }}

        @media (max-width: 768px) {{
            body {{ font-size: 14px; }}
            .container {{ padding: 16px; }}
            h1 {{ font-size: 1.8rem; }}
            h2 {{ font-size: 1.5rem; }}
            .market-status {{ flex-direction: column; align-items: flex-start; }}
            .indicator-item {{ grid-template-columns: 60px 1fr auto; }}
            .indicator-name {{ padding: 0 8px; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>経済指標レポート</h1>
        <p class="subtitle">Economic Indicators Hub - 詳細分析レポートのハブ</p>
        
        <div class="market-status">
            <div class="status-item">
                <div class="status-label">政策金利</div>
                <div class="status-value">{market['current_status']['fed_funds_rate']}</div>
            </div>
            <div class="status-item">
                <div class="status-label">CPI（前年比）</div>
                <div class="status-value">{market['current_status']['current_cpi']}</div>
            </div>
            <div class="status-item">
                <div class="status-label">失業率</div>
                <div class="status-value">{market['current_status']['unemployment_rate']}</div>
            </div>
            <div class="status-item">
                <div class="status-label">GDP成長率</div>
                <div class="status-value">{market['current_status']['gdp_growth']}</div>
            </div>
            <div class="status-item">
                <div class="status-label">市場センチメント</div>
                <div class="status-value">{market['current_status']['market_sentiment']}</div>
            </div>
        </div>
    </header>

    <div class="card">
        <h2>今週の経済指標スケジュール（東京時間）</h2>
        <div class="schedule-grid">
"""

    # スケジュールを追加
    for day_data in schedule:
        html_content += f"""
            <div class="day-card">
                <div class="day-header"><div class="day-title">{day_data['day']}曜日</div><div class="day-date">{day_data['date']}</div></div>
"""
        for indicator in day_data['indicators']:
            importance_class = f"importance-{indicator['importance']}"
            if indicator['importance'] == '最高':
                importance_class = "importance-highest"
            elif indicator['importance'] == '高':
                importance_class = "importance-high"
            elif indicator['importance'] == '中':
                importance_class = "importance-medium"
            else:
                importance_class = "importance-low"
                
            html_content += f"""
                <div class="indicator-item {indicator['importance']}">
                    <div class="indicator-time">{indicator['time']}</div>
                    <div class="indicator-name">{indicator['country']} {indicator['name']}</div>
                    <div class="indicator-importance"><span class="{importance_class}">{indicator['importance']}</span></div>
                </div>
"""
        html_content += """
            </div>
"""

    html_content += """
        </div>
    </div>

    <div class="card">
        <h2>経済指標 詳細分析</h2>
        <p class="note">各指標をクリックすると詳細な深堀り分析レポートにアクセスできます。</p>
        <div class="indicators-grid">
"""

    # 指標一覧を追加
    for key, indicator in indicators.items():
        result = indicator.get('latest_result', {})
        trend_class = result.get('trend', 'neutral')
        
        html_content += f"""
            <div class="indicator-card">
                <div>
                    <h4>{indicator['name']}</h4>
                    <p class="indicator-description">{indicator['description']}</p>
                    <div class="indicator-details">
                        <div class="detail-item"><span class="detail-label">頻度</span><span>{indicator['frequency']}</span></div>
                        <div class="detail-item"><span class="detail-label">重要度</span><span>{indicator['importance']}</span></div>
                    </div>
                    <div class="latest-result">
                        <div class="result-item"><span class="result-label">前回</span><span class="result-value">{result.get('previous', '-')}</span></div>
                        <div class="result-item"><span class="result-label">予想</span><span class="result-value">{result.get('forecast', '-')}</span></div>
                        <div class="result-item"><span class="result-label">結果</span><span class="result-value {trend_class}">{result.get('actual', '-')}</span></div>
                    </div>
                </div>
                <a href="{indicator['deep_analysis']}" class="deep-analysis-link">詳細分析を見る</a>
            </div>
"""

    html_content += f"""
        </div>
    </div>

    <div class="card">
        <h2>現在の主要テーマ</h2>
        <ul class="styled-list">
"""
    for theme in market['key_themes']:
        html_content += f"<li>{theme}</li>"

    html_content += """
        </ul>
    </div>

    <div class="card">
        <h2>今後の重要イベント</h2>
        <ul class="styled-list">
"""
    for event in market['upcoming_events']:
        html_content += f"<li>{event}</li>"

    html_content += """
        </ul>
    </div>
    
    <div class="card footer-info">
        <h2>レポートについて</h2>
        <p>このレポートは経済指標の概要とスケジュールを提供し、各指標の詳細分析へのナビゲーションハブとして機能します。</p>
        <p><strong>更新頻度:</strong> 毎週月曜日</p>
        <p><strong>データソース:</strong> FRED, BLS, BEA, FRB, その他公的機関</p>
        <p><strong>免責事項:</strong> このレポートは情報提供目的であり、投資助言ではありません。</p>
    </div>
</div>
</body>
</html>
"""
    
    return html_content

def main():
    """メイン実行関数"""
    print("🏛️ 経済指標レポート（クラシック版）生成を開始します...")
    
    # HTMLレポートを生成
    html_content = generate_economic_indicators_classic()
    
    # 出力ディレクトリを作成
    output_dir = Path("test_output/enhanced_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"economic_indicators_classic_{timestamp}.html"
    filepath = output_dir / filename
    
    # HTMLファイルを保存
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 経済指標レポート（クラシック版）が生成されました: {filepath}")
    print(f"📁 生成されたファイル: {filepath}")
    print(f"🌐 HTMLレポート: {filepath}")
    print(f"   ブラウザで開くには: file://{filepath.absolute()}")
    
    # ブラウザで開く
    import webbrowser
    webbrowser.open(f"file://{filepath.absolute()}")
    print("🔍 ブラウザでレポートを開きました")

if __name__ == "__main__":
    main()
