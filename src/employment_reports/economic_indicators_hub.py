#!/usr/bin/env python3
"""
Economic Indicators Hub Report
経済指標レポート（標準版）- 全深堀りレポートのハブ
"""

import json
from pathlib import Path
import sys
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def get_economic_schedule():
    """経済指標スケジュールを取得"""
    today = datetime.now()
    
    # 今週のスケジュール（サンプル）
    schedule = []
    
    # 月曜日
    monday = today - timedelta(days=today.weekday())
    schedule.append({
        "date": monday.strftime("%m/%d"),
        "day": "月",
        "indicators": [
            {"time": "09:30", "name": "ISM製造業PMI", "importance": "高", "country": "🇺🇸"},
            {"time": "10:00", "name": "建設支出", "importance": "中", "country": "🇺🇸"}
        ]
    })
    
    # 火曜日
    tuesday = monday + timedelta(days=1)
    schedule.append({
        "date": tuesday.strftime("%m/%d"),
        "day": "火",
        "indicators": [
            {"time": "09:30", "name": "JOLTS求人", "importance": "高", "country": "🇺🇸"},
            {"time": "10:00", "name": "工場受注", "importance": "中", "country": "🇺🇸"},
            {"time": "14:00", "name": "消費者信頼感指数", "importance": "中", "country": "🇺🇸"}
        ]
    })
    
    # 水曜日
    wednesday = monday + timedelta(days=2)
    schedule.append({
        "date": wednesday.strftime("%m/%d"),
        "day": "水",
        "indicators": [
            {"time": "09:30", "name": "ADP雇用統計", "importance": "高", "country": "🇺🇸"},
            {"time": "10:00", "name": "ISM非製造業PMI", "importance": "高", "country": "🇺🇸"},
            {"time": "14:00", "name": "FOMC議事録", "importance": "高", "country": "🇺🇸"}
        ]
    })
    
    # 木曜日
    thursday = monday + timedelta(days=3)
    schedule.append({
        "date": thursday.strftime("%m/%d"),
        "day": "木",
        "indicators": [
            {"time": "09:30", "name": "週次失業保険申請", "importance": "中", "country": "🇺🇸"},
            {"time": "10:00", "name": "貿易収支", "importance": "中", "country": "🇺🇸"},
            {"time": "14:00", "name": "消費者信用残高", "importance": "低", "country": "🇺🇸"}
        ]
    })
    
    # 金曜日
    friday = monday + timedelta(days=4)
    schedule.append({
        "date": friday.strftime("%m/%d"),
        "day": "金",
        "indicators": [
            {"time": "09:30", "name": "雇用統計", "importance": "最高", "country": "🇺🇸"},
            {"time": "10:00", "name": "消費者物価指数", "importance": "高", "country": "🇺🇸"},
            {"time": "14:00", "name": "ミシガン消費者信頼感", "importance": "中", "country": "🇺🇸"}
        ]
    })
    
    return schedule

def get_indicators_overview():
    """各経済指標の概要を取得"""
    return {
        "employment": {
            "name": "雇用統計",
            "description": "非農業部門雇用者数、失業率、平均時給など",
            "frequency": "月次（第1金曜日）",
            "importance": "最高",
            "impact": "FRB政策、株式・債券・為替市場に大きな影響",
            "deep_analysis": "employment_deep_analysis.html"
        },
        "inflation": {
            "name": "物価指標",
            "description": "CPI、PCE、PPIなど消費者・生産者物価指数",
            "frequency": "月次",
            "importance": "高",
            "impact": "FRB政策、金利、債券市場に直接影響",
            "deep_analysis": "inflation_deep_analysis.html"
        },
        "gdp": {
            "name": "GDP・成長指標",
            "description": "GDP、個人消費、設備投資など経済成長指標",
            "frequency": "四半期",
            "importance": "高",
            "impact": "経済全体の健全性、長期トレンドの判断",
            "deep_analysis": "gdp_deep_analysis.html"
        },
        "manufacturing": {
            "name": "製造業指標",
            "description": "ISM製造業PMI、工業生産、設備稼働率など",
            "frequency": "月次",
            "importance": "中-高",
            "impact": "景気サイクル、セクター別投資判断",
            "deep_analysis": "manufacturing_deep_analysis.html"
        },
        "consumer": {
            "name": "消費者指標",
            "description": "個人消費、小売売上高、消費者信頼感など",
            "frequency": "月次",
            "importance": "中-高",
            "impact": "内需動向、消費関連株への影響",
            "deep_analysis": "consumer_deep_analysis.html"
        },
        "housing": {
            "name": "住宅指標",
            "description": "新築住宅着工、住宅販売、住宅価格指数など",
            "frequency": "月次",
            "importance": "中",
            "impact": "金利政策、住宅関連株、地域経済",
            "deep_analysis": "housing_deep_analysis.html"
        },
        "trade": {
            "name": "貿易・国際収支",
            "description": "貿易収支、経常収支、資本収支など",
            "frequency": "月次",
            "importance": "中",
            "impact": "為替レート、貿易関連株、国際関係",
            "deep_analysis": "trade_deep_analysis.html"
        },
        "monetary": {
            "name": "金融政策",
            "description": "FOMC声明、議事録、FRB関係者発言など",
            "frequency": "随時",
            "importance": "最高",
            "impact": "全資産クラス、金利、為替に最大影響",
            "deep_analysis": "monetary_deep_analysis.html"
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

def generate_economic_indicators_hub():
    """経済指標ハブレポートを生成"""
    
    schedule = get_economic_schedule()
    indicators = get_indicators_overview()
    market = get_market_overview()
    
    html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>経済指標レポート（標準版） - Economic Indicators Hub</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --primary: #2c3e50;
            --secondary: #3498db;
            --success: #27ae60;
            --warning: #f39c12;
            --danger: #e74c3c;
            --light: #ecf0f1;
            --dark: #34495e;
            --muted: #7f8c8d;
            --border: #bdc3c7;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--dark);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}

        h1 {{
            color: var(--primary);
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }}

        .subtitle {{
            color: var(--muted);
            font-size: 1.1rem;
            margin-bottom: 20px;
        }}

        .market-status {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}

        .status-item {{
            background: var(--light);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}

        .status-value {{
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--primary);
        }}

        .status-label {{
            font-size: 0.9rem;
            color: var(--muted);
            margin-top: 5px;
        }}

        .card {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        h2 {{
            color: var(--primary);
            font-size: 1.8rem;
            margin-bottom: 20px;
            border-bottom: 3px solid var(--secondary);
            padding-bottom: 10px;
        }}

        h3 {{
            color: var(--dark);
            font-size: 1.3rem;
            margin: 20px 0 10px 0;
        }}

        .schedule-grid {{
            display: grid;
            gap: 15px;
        }}

        .day-card {{
            background: var(--light);
            border-radius: 10px;
            padding: 20px;
            border-left: 5px solid var(--secondary);
        }}

        .day-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}

        .day-title {{
            font-size: 1.2rem;
            font-weight: bold;
            color: var(--primary);
        }}

        .day-date {{
            background: var(--secondary);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9rem;
        }}

        .indicator-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            background: white;
            border-radius: 8px;
            border-left: 4px solid var(--success);
        }}

        .indicator-item.high {{
            border-left-color: var(--warning);
        }}

        .indicator-item.highest {{
            border-left-color: var(--danger);
        }}

        .indicator-time {{
            font-weight: bold;
            color: var(--primary);
            min-width: 60px;
        }}

        .indicator-name {{
            flex: 1;
            margin: 0 15px;
        }}

        .indicator-importance {{
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: bold;
        }}

        .importance-low {{
            background: var(--light);
            color: var(--muted);
        }}

        .importance-medium {{
            background: #fff3cd;
            color: #856404;
        }}

        .importance-high {{
            background: #f8d7da;
            color: #721c24;
        }}

        .importance-highest {{
            background: var(--danger);
            color: white;
        }}

        .indicators-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }}

        .indicator-card {{
            background: var(--light);
            border-radius: 12px;
            padding: 20px;
            border: 2px solid transparent;
            transition: all 0.3s ease;
            cursor: pointer;
        }}

        .indicator-card:hover {{
            border-color: var(--secondary);
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        }}

        .indicator-card h4 {{
            color: var(--primary);
            font-size: 1.3rem;
            margin-bottom: 10px;
        }}

        .indicator-description {{
            color: var(--muted);
            margin-bottom: 15px;
            line-height: 1.5;
        }}

        .indicator-details {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }}

        .detail-item {{
            background: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9rem;
        }}

        .detail-label {{
            font-weight: bold;
            color: var(--primary);
        }}

        .detail-value {{
            color: var(--muted);
        }}

        .deep-analysis-link {{
            display: inline-block;
            background: var(--secondary);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s ease;
        }}

        .deep-analysis-link:hover {{
            background: var(--primary);
            transform: scale(1.05);
        }}

        .themes-list {{
            list-style: none;
            padding: 0;
        }}

        .themes-list li {{
            background: var(--light);
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid var(--warning);
        }}

        .events-list {{
            list-style: none;
            padding: 0;
        }}

        .events-list li {{
            background: var(--light);
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid var(--success);
        }}

        .note {{
            background: #e3f2fd;
            border-left: 4px solid var(--secondary);
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
            font-style: italic;
            color: var(--dark);
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            h1 {{
                font-size: 2rem;
            }}
            
            .market-status {{
                grid-template-columns: 1fr;
            }}
            
            .indicators-grid {{
                grid-template-columns: 1fr;
            }}
            
            .indicator-details {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>📊 経済指標レポート（標準版）</h1>
        <p class="subtitle">Economic Indicators Hub - 全深堀りレポートのハブ</p>
        
        <div class="market-status">
            <div class="status-item">
                <div class="status-value">{market['current_status']['fed_funds_rate']}</div>
                <div class="status-label">政策金利</div>
            </div>
            <div class="status-item">
                <div class="status-value">{market['current_status']['current_cpi']}</div>
                <div class="status-label">CPI（前年比）</div>
            </div>
            <div class="status-item">
                <div class="status-value">{market['current_status']['unemployment_rate']}</div>
                <div class="status-label">失業率</div>
            </div>
            <div class="status-item">
                <div class="status-value">{market['current_status']['gdp_growth']}</div>
                <div class="status-label">GDP成長率</div>
            </div>
            <div class="status-item">
                <div class="status-value">{market['current_status']['market_sentiment']}</div>
                <div class="status-label">市場センチメント</div>
            </div>
        </div>
    </header>

    <!-- 今週の経済指標スケジュール -->
    <div class="card">
        <h2>📅 今週の経済指標スケジュール</h2>
        <div class="schedule-grid">
"""

    # スケジュールを追加
    for day_data in schedule:
        html_content += f"""
            <div class="day-card">
                <div class="day-header">
                    <div class="day-title">{day_data['day']}曜日</div>
                    <div class="day-date">{day_data['date']}</div>
                </div>
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
                    <div class="indicator-importance {importance_class}">{indicator['importance']}</div>
                </div>
"""
        html_content += """
            </div>
"""

    html_content += """
        </div>
    </div>

    <!-- 経済指標一覧 -->
    <div class="card">
        <h2>📈 経済指標一覧</h2>
        <p class="note">各指標をクリックすると詳細な深堀り分析レポートにアクセスできます</p>
        <div class="indicators-grid">
"""

    # 指標一覧を追加
    for key, indicator in indicators.items():
        html_content += f"""
            <div class="indicator-card" onclick="window.open('{indicator['deep_analysis']}', '_blank')">
                <h4>{indicator['name']}</h4>
                <p class="indicator-description">{indicator['description']}</p>
                <div class="indicator-details">
                    <div class="detail-item">
                        <div class="detail-label">頻度</div>
                        <div class="detail-value">{indicator['frequency']}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">重要度</div>
                        <div class="detail-value">{indicator['importance']}</div>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">市場への影響</div>
                    <div class="detail-value">{indicator['impact']}</div>
                </div>
                <a href="{indicator['deep_analysis']}" class="deep-analysis-link" target="_blank">
                    🔍 深堀り分析を見る
                </a>
            </div>
"""

    html_content += f"""
        </div>
    </div>

    <!-- 主要テーマ -->
    <div class="card">
        <h2>🎯 現在の主要テーマ</h2>
        <ul class="themes-list">
"""
    for theme in market['key_themes']:
        html_content += f"<li>{theme}</li>"

    html_content += """
        </ul>
    </div>

    <!-- 今後の重要イベント -->
    <div class="card">
        <h2>📋 今後の重要イベント</h2>
        <ul class="events-list">
"""
    for event in market['upcoming_events']:
        html_content += f"<li>{event}</li>"

    html_content += """
        </ul>
    </div>

    <!-- フッター -->
    <div class="card">
        <h2>ℹ️ レポートについて</h2>
        <p>このレポートは経済指標の概要とスケジュールを提供し、各指標の詳細分析へのナビゲーションハブとして機能します。</p>
        <p><strong>更新頻度:</strong> 毎週月曜日</p>
        <p><strong>データソース:</strong> FRED, BLS, BEA, FRB, その他公的機関</p>
        <p><strong>免責事項:</strong> このレポートは情報提供目的であり、投資助言ではありません。</p>
    </div>
</div>

<script>
// カードホバーエフェクト
document.querySelectorAll('.indicator-card').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-5px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

// スケジュールの重要性に応じた色分け
document.querySelectorAll('.indicator-item').forEach(item => {
    const importance = item.classList.contains('high') ? 'high' : 
                      item.classList.contains('highest') ? 'highest' : 'normal';
    
    if (importance === 'high') {
        item.style.background = 'linear-gradient(90deg, #fff3cd 0%, #ffffff 100%)';
    } else if (importance === 'highest') {
        item.style.background = 'linear-gradient(90deg, #f8d7da 0%, #ffffff 100%)';
    }
});
</script>
</body>
</html>
"""
    
    return html_content

def main():
    """メイン実行関数"""
    print("🏛️ 経済指標レポート（標準版）生成を開始します...")
    
    # HTMLレポートを生成
    html_content = generate_economic_indicators_hub()
    
    # 出力ディレクトリを作成
    output_dir = Path("test_output/enhanced_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"economic_indicators_hub_{timestamp}.html"
    filepath = output_dir / filename
    
    # HTMLファイルを保存
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 経済指標レポート（標準版）が生成されました: {filepath}")
    print(f"📁 生成されたファイル: {filepath}")
    print(f"🌐 HTMLレポート: {filepath}")
    print(f"   ブラウザで開くには: file://{filepath.absolute()}")
    
    # ブラウザで開く
    import webbrowser
    webbrowser.open(f"file://{filepath.absolute()}")
    print("🔍 ブラウザでレポートを開きました")

if __name__ == "__main__":
    main()
