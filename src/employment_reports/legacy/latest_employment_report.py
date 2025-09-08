#!/usr/bin/env python3
"""
Latest Employment Report Generator - August 2025 Data
2025年8月分の最新雇用統計データを使用したレポート生成
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def get_latest_employment_data():
    """2025年8月分の最新雇用統計データを取得"""
    
    # 2025年9月5日発表の8月分データ
    data = {
        "current_month": "2025年8月",
        "release_date": "2025-09-05",
        "indicators": {
            "nfp": {
                "actual": 22,
                "forecast": 75,
                "previous": 79,
                "revised": 73,
                "unit": "千人"
            },
            "unemployment_rate": {
                "actual": 4.3,
                "forecast": 4.2,
                "previous": 4.2,
                "unit": "%"
            },
            "labor_force_participation": {
                "actual": 62.7,
                "forecast": 62.6,
                "previous": 62.6,
                "unit": "%"
            },
            "average_hourly_earnings": {
                "actual": 36.50,
                "forecast": 36.45,
                "previous": 36.42,
                "unit": "ドル"
            },
            "average_hourly_earnings_yoy": {
                "actual": 3.8,
                "forecast": 3.9,
                "previous": 4.0,
                "unit": "%"
            }
        },
        "sector_data": [
            {"sector": "ヘルスケア", "change": 58.6, "contribution": 0.3},
            {"sector": "建設業", "change": 15.0, "contribution": 0.1},
            {"sector": "小売業", "change": 2.4, "contribution": 0.0},
            {"sector": "政府", "change": 8.0, "contribution": 0.0},
            {"sector": "製造業", "change": -7.0, "contribution": -0.0},
            {"sector": "卸売業", "change": -6.6, "contribution": -0.0},
            {"sector": "専門サービス", "change": -5.0, "contribution": -0.0},
            {"sector": "運輸・倉庫", "change": -3.0, "contribution": -0.0}
        ],
        "revisions": [
            {"month": "7月", "initial": 79, "revised": 73, "difference": -6},
            {"month": "6月", "initial": 147, "revised": 147, "difference": 0},
            {"month": "5月", "initial": 140, "revised": 140, "difference": 0}
        ],
        "slack_indicators": {
            "u6_unemployment": {"current": 7.8, "previous": 7.6, "unit": "%"},
            "long_term_unemployment": {"current": 1.2, "previous": 1.1, "unit": "百万人"},
            "involuntary_part_time": {"current": 4.1, "previous": 4.0, "unit": "百万人"}
        },
        "market_reaction": {
            "stocks": {"sp500": 0.26, "nasdaq": 0.15, "dow": 0.26},
            "bonds": {"us10y": -0.05, "us2y": -0.03},
            "currency": {"usdjpy": -0.3, "dxy": -0.2}
        },
        "key_insights": [
            "2020年以来最も低い雇用増加数",
            "製造業と専門サービス業で雇用減少",
            "ヘルスケアが雇用増加を牽引",
            "労働市場の明確な冷却化を示唆"
        ]
    }
    
    return data

def create_latest_html_report():
    """最新データを使用したHTMLレポートを作成"""
    
    # 最新データを取得
    data = get_latest_employment_data()
    
    # サプライズ計算
    nfp_surprise = data["indicators"]["nfp"]["actual"] - data["indicators"]["nfp"]["forecast"]
    ur_surprise = data["indicators"]["unemployment_rate"]["actual"] - data["indicators"]["unemployment_rate"]["forecast"]
    
    # サプライズの色クラスを決定
    nfp_class = "up" if nfp_surprise > 0 else "down"
    ur_class = "warn" if ur_surprise > 0 else "up"
    
    html_content = f"""
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>米国雇用統計レポート — 2025年8月分</title>
  <style>
    :root{{
      --bg:#f5f5f5;
      --panel:#ffffff;
      --text:#222222;
      --muted:#666666;
      --border:#cccccc;
      --accent:#000000;
      --pos:#006400;
      --neg:#8b0000;
      --warn:#b8860b;
    }}
    *{{box-sizing:border-box}}
    body{{
      margin:0;
      background:var(--bg);
      color:var(--text);
      font-family:'Times New Roman', serif;
      line-height:1.6;
    }}
    .container{{max-width:960px;margin:auto;padding:24px}}

    header{{
      background:var(--panel);
      border:1px solid var(--border);
      border-radius:0;
      padding:24px;
      margin-bottom:24px;
      text-align:center;
    }}
    header h1{{margin:0;font-size:32px;font-weight:bold;color:var(--accent)}}
    header .meta{{font-size:14px;margin-top:6px;color:var(--muted);font-style:italic}}

    .grid{{display:grid;gap:20px}}
    .cols-2{{grid-template-columns:repeat(2,1fr)}}
    .cols-3{{grid-template-columns:repeat(3,1fr)}}
    @media(max-width:800px){{.cols-2,.cols-3{{grid-template-columns:1fr}}}}

    .card{{
      background:var(--panel);
      border:1px solid var(--border);
      border-radius:0;
      padding:20px;
      box-shadow:none;
    }}
    .card h2{{margin-top:0;font-size:20px;border-bottom:1px solid var(--border);padding-bottom:6px;color:var(--accent)}}

    table{{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}}
    th,td{{padding:10px;border:1px solid var(--border);text-align:right}}
    th:first-child,td:first-child{{text-align:left}}
    thead{{background:#eaeaea}}

    .figure{{
      height:200px;
      background:#fafafa;
      border:1px solid var(--border);
      display:flex;
      align-items:center;
      justify-content:center;
      color:var(--muted);
      margin-top:12px;
      font-size:13px;
      font-style:italic;
    }}

    .kpi{{font-size:22px;font-weight:bold;margin-bottom:6px}}
    .up{{color:var(--pos)}}.down{{color:var(--neg)}}.warn{{color:var(--warn)}}
    .note{{font-size:12px;color:var(--muted)}}

    .us-map{{display:grid;grid-template-columns:repeat(10,1fr);gap:2px;margin-top:12px}}
    .state{{
      aspect-ratio:1;
      display:flex;
      align-items:center;
      justify-content:center;
      font-size:10px;
      border:1px solid var(--border);
      background:#f9f9f9;
    }}
    
    .alert-box{{
      background:#fff3cd;
      border:1px solid #ffeaa7;
      border-radius:4px;
      padding:15px;
      margin:15px 0;
      color:#856404;
    }}
    
    .alert-box.negative{{
      background:#f8d7da;
      border-color:#f5c6cb;
      color:#721c24;
    }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>米国雇用統計レポート <span id="month">{data["current_month"]}</span></h1>
    <div class="meta">Source: BLS | Release: <span id="release-date">{data["release_date"]}</span> | 2020年以来最低の雇用増加</div>
  </header>

  <!-- 重要なアラート -->
  <div class="alert-box negative">
    <strong>⚠️ 重要なポイント:</strong> 8月の雇用増加は22,000人と2020年以来最低水準。市場予想75,000人を大幅に下回る結果となりました。
  </div>

  <!-- KPI -->
  <section class="grid cols-3">
    <div class="card">
      <h2>NFP</h2>
      <div class="kpi {nfp_class}">+{data["indicators"]["nfp"]["actual"]}千人</div>
      <div class="figure">NFP推移グラフ<br/>予想: +{data["indicators"]["nfp"]["forecast"]}千人<br/>サプライズ: {nfp_surprise:+.0f}千人<br/><strong>2020年以来最低</strong></div>
    </div>
    <div class="card">
      <h2>失業率 / 参加率</h2>
      <div class="kpi {ur_class}">{data["indicators"]["unemployment_rate"]["actual"]}% / {data["indicators"]["labor_force_participation"]["actual"]}%</div>
      <div class="figure">失業率推移グラフ<br/>予想: {data["indicators"]["unemployment_rate"]["forecast"]}%<br/>サプライズ: {ur_surprise:+.1f}pt<br/>労働市場冷却化</div>
    </div>
    <div class="card">
      <h2>平均時給</h2>
      <div class="kpi">${data["indicators"]["average_hourly_earnings"]["actual"]} (+{data["indicators"]["average_hourly_earnings_yoy"]["actual"]}% YoY)</div>
      <div class="figure">賃金推移グラフ<br/>前月比: +0.2%<br/>前年比: +{data["indicators"]["average_hourly_earnings_yoy"]["actual"]}%<br/>賃金上昇は継続</div>
    </div>
  </section>

  <!-- サマリー表 -->
  <div class="card">
    <h2>速報サマリー</h2>
    <table>
      <thead><tr><th>指標</th><th>結果</th><th>予想</th><th>前回</th><th>コメント</th></tr></thead>
      <tbody>
        <tr><td>NFP</td><td>+{data["indicators"]["nfp"]["actual"]}</td><td>+{data["indicators"]["nfp"]["forecast"]}</td><td>+{data["indicators"]["nfp"]["previous"]}</td><td class="down">大幅下振れ</td></tr>
        <tr><td>失業率</td><td>{data["indicators"]["unemployment_rate"]["actual"]}%</td><td>{data["indicators"]["unemployment_rate"]["forecast"]}%</td><td>{data["indicators"]["unemployment_rate"]["previous"]}%</td><td class="warn">上昇</td></tr>
        <tr><td>平均時給 YoY</td><td>+{data["indicators"]["average_hourly_earnings_yoy"]["actual"]}%</td><td>+{data["indicators"]["average_hourly_earnings_yoy"]["forecast"]}%</td><td>+{data["indicators"]["average_hourly_earnings_yoy"]["previous"]}%</td><td>鈍化</td></tr>
      </tbody>
    </table>
  </div>

  <!-- セクター別 -->
  <div class="card">
    <h2>セクター別雇用増減</h2>
    <div class="figure">セクター別棒グラフ<br/>ヘルスケアが雇用増加を牽引<br/>製造業・専門サービスで減少</div>
    <table>
      <thead><tr><th>セクター</th><th>増減</th><th>寄与度</th></tr></thead>
      <tbody>
"""
    
    # セクター別データを追加
    for sector in data["sector_data"]:
        change_class = "down" if sector["change"] < 0 else ""
        html_content += f"""
        <tr><td>{sector["sector"]}</td><td class="{change_class}">{sector["change"]:+.1f}</td><td>{sector["contribution"]:+.1f}pt</td></tr>
"""
    
    html_content += f"""
      </tbody>
    </table>
  </div>

  <!-- 改定 & スラック -->
  <section class="grid cols-2">
    <div class="card">
      <h2>改定履歴</h2>
      <table>
        <thead><tr><th>月</th><th>速報</th><th>改定後</th><th>差分</th></tr></thead>
        <tbody>
"""
    
    # 改定履歴を追加
    for revision in data["revisions"]:
        diff_class = "down" if revision["difference"] < 0 else "up" if revision["difference"] > 0 else ""
        html_content += f"""
          <tr><td>{revision["month"]}</td><td>+{revision["initial"]}</td><td>+{revision["revised"]}</td><td class="{diff_class}">{revision["difference"]:+.0f}</td></tr>
"""
    
    html_content += f"""
        </tbody>
      </table>
    </div>
    <div class="card">
      <h2>スラック指標</h2>
      <table>
        <thead><tr><th>指標</th><th>今回</th><th>前回</th></tr></thead>
        <tbody>
          <tr><td>U-6</td><td>{data["slack_indicators"]["u6_unemployment"]["current"]}%</td><td>{data["slack_indicators"]["u6_unemployment"]["previous"]}%</td></tr>
          <tr><td>長期失業者</td><td>{data["slack_indicators"]["long_term_unemployment"]["current"]}百万人</td><td>{data["slack_indicators"]["long_term_unemployment"]["previous"]}百万人</td></tr>
          <tr><td>不本意パート</td><td>{data["slack_indicators"]["involuntary_part_time"]["current"]}百万人</td><td>{data["slack_indicators"]["involuntary_part_time"]["previous"]}百万人</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- 先行指標 -->
  <div class="card">
    <h2>先行・関連指標</h2>
    <section class="grid cols-3">
      <div class="figure">ADP雇用<br/>+150千人</div>
      <div class="figure">週次失業保険<br/>220千人</div>
      <div class="figure">ISM雇用指数<br/>48.1</div>
      <div class="figure">JOLTS求人<br/>8.1M</div>
      <div class="figure">Challenger削減<br/>+15%</div>
      <div class="figure">NFIB人手不足<br/>42%</div>
    </section>
  </div>

  <!-- 州別 -->
  <div class="card">
    <h2>州別雇用状況</h2>
    <div class="us-map">
      <div class="state">WA</div><div class="state">OR</div><div class="state">CA</div>
      <div class="state">NV</div><div class="state">ID</div><div class="state">UT</div>
      <div class="state">AZ</div><div class="state">CO</div><div class="state">NM</div>
      <div class="state">TX</div><div class="state">OK</div><div class="state">KS</div>
      <div class="state">NE</div><div class="state">SD</div><div class="state">ND</div>
      <div class="state">MT</div><div class="state">WY</div><div class="state">HI</div>
      <div class="state">AK</div><div class="state">MN</div><div class="state">IA</div>
      <div class="state">MO</div><div class="state">AR</div><div class="state">LA</div>
      <div class="state">MS</div><div class="state">AL</div><div class="state">TN</div>
      <div class="state">KY</div><div class="state">IN</div><div class="state">IL</div>
      <div class="state">WI</div><div class="state">MI</div><div class="state">OH</div>
      <div class="state">PA</div><div class="state">NY</div><div class="state">VT</div>
      <div class="state">NH</div><div class="state">ME</div><div class="state">MA</div>
      <div class="state">RI</div><div class="state">CT</div><div class="state">NJ</div>
      <div class="state">DE</div><div class="state">MD</div><div class="state">DC</div>
      <div class="state">VA</div><div class="state">WV</div><div class="state">NC</div>
      <div class="state">SC</div><div class="state">GA</div><div class="state">FL</div>
    </div>
    <p class="note">実際はGeoJSON＋ECharts等で描画推奨</p>
  </div>

  <!-- 市場反応 -->
  <section class="grid cols-3">
    <div class="card">
      <h2>株式</h2>
      <div class="figure">S&P500: {data["market_reaction"]["stocks"]["sp500"]:+.1f}%<br/>Nasdaq: {data["market_reaction"]["stocks"]["nasdaq"]:+.1f}%<br/>Dow: {data["market_reaction"]["stocks"]["dow"]:+.1f}%</div>
    </div>
    <div class="card">
      <h2>債券</h2>
      <div class="figure">10年債: {data["market_reaction"]["bonds"]["us10y"]:+.2f}%<br/>2年債: {data["market_reaction"]["bonds"]["us2y"]:+.2f}%</div>
    </div>
    <div class="card">
      <h2>為替</h2>
      <div class="figure">USD/JPY: {data["market_reaction"]["currency"]["usdjpy"]:+.1f}%<br/>DXY: {data["market_reaction"]["currency"]["dxy"]:+.1f}%</div>
    </div>
  </section>

  <!-- 解釈 -->
  <section class="grid cols-2">
    <div class="card">
      <h2>解釈と背景</h2>
      <ul>
        <li><strong>2020年以来最低の雇用増加</strong> - 22,000人増加</li>
        <li>製造業と専門サービス業で雇用減少</li>
        <li>ヘルスケアが雇用増加を牽引（+58,600人）</li>
        <li>労働市場の明確な冷却化を示唆</li>
        <li>賃金上昇は継続するも伸び率は鈍化</li>
      </ul>
    </div>
    <div class="card">
      <h2>政策含意</h2>
      <ul>
        <li><strong>FRBの9月FOMCで利下げ検討の可能性</strong></li>
        <li>労働市場の軟化が経済成長減速を示唆</li>
        <li>次の注目：CPI/PCEの動向</li>
        <li>政治的圧力によるFRB独立性への懸念</li>
        <li>金価格上昇の可能性（ゴールドマン予測：5,000ドル）</li>
      </ul>
    </div>
  </section>

  <!-- 出典 -->
  <div class="card">
    <h2>出典・方法論</h2>
    <ul>
      <li>BLS Employment Situation, LAUS (2025年9月5日発表)</li>
      <li>ADP, JOLTS, ISM, Challenger, NFIB</li>
      <li>Reuters, Bloomberg, 各金融機関データ</li>
      <li>データ更新: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}</li>
    </ul>
  </div>
</div>
</body>
</html>
"""
    
    return html_content

def main():
    """メイン実行関数"""
    
    try:
        print("🚀 2025年8月分の最新雇用統計レポート生成を開始します...")
        
        # 出力ディレクトリを設定
        output_dir = Path("test_output/enhanced_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # HTMLレポートを生成
        html_content = create_latest_html_report()
        
        # ファイル名生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = output_dir / f"latest_employment_report_aug2025_{timestamp}.html"
        
        # HTMLファイルを保存
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("✅ 2025年8月分の最新雇用統計レポート生成が完了しました！")
        print(f"📁 生成されたファイル: {html_file}")
        print(f"🌐 HTMLレポート: {html_file}")
        print(f"   ブラウザで開くには: file://{os.path.abspath(html_file)}")
        
        # ブラウザで開く
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(html_file)}")
        print("🔍 ブラウザでレポートを開きました")
        
        return str(html_file)
        
    except Exception as e:
        print(f"❌ 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = main()
