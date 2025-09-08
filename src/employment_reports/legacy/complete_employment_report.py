#!/usr/bin/env python3
"""
Complete Employment Report Generator with Charts and State Data
グラフと州別データを含む完全な雇用統計レポート生成
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def get_complete_employment_data():
    """完全な雇用統計データを取得（グラフ用データと州別データ含む）"""
    
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
        # グラフ用の時系列データ
        "chart_data": {
            "nfp_trend": [
                {"month": "2024-08", "value": 150, "forecast": 170},
                {"month": "2024-09", "value": 297, "forecast": 170},
                {"month": "2024-10", "value": 150, "forecast": 180},
                {"month": "2024-11", "value": 199, "forecast": 180},
                {"month": "2024-12", "value": 216, "forecast": 170},
                {"month": "2025-01", "value": 229, "forecast": 180},
                {"month": "2025-02", "value": 151, "forecast": 200},
                {"month": "2025-03", "value": 175, "forecast": 200},
                {"month": "2025-04", "value": 175, "forecast": 240},
                {"month": "2025-05", "value": 140, "forecast": 180},
                {"month": "2025-06", "value": 147, "forecast": 190},
                {"month": "2025-07", "value": 73, "forecast": 190},
                {"month": "2025-08", "value": 22, "forecast": 75}
            ],
            "unemployment_trend": [
                {"month": "2024-08", "value": 3.8, "forecast": 4.0},
                {"month": "2024-09", "value": 3.8, "forecast": 3.9},
                {"month": "2024-10", "value": 3.9, "forecast": 3.8},
                {"month": "2024-11", "value": 3.7, "forecast": 3.9},
                {"month": "2024-12", "value": 3.7, "forecast": 3.8},
                {"month": "2025-01", "value": 3.7, "forecast": 3.8},
                {"month": "2025-02", "value": 3.9, "forecast": 3.8},
                {"month": "2025-03", "value": 3.8, "forecast": 3.9},
                {"month": "2025-04", "value": 3.9, "forecast": 3.8},
                {"month": "2025-05", "value": 4.0, "forecast": 3.9},
                {"month": "2025-06", "value": 4.1, "forecast": 4.0},
                {"month": "2025-07", "value": 4.2, "forecast": 4.1},
                {"month": "2025-08", "value": 4.3, "forecast": 4.2}
            ],
            "wage_trend": [
                {"month": "2024-08", "value": 35.25, "forecast": 35.00},
                {"month": "2024-09", "value": 35.40, "forecast": 35.10},
                {"month": "2024-10", "value": 35.50, "forecast": 35.20},
                {"month": "2024-11", "value": 35.65, "forecast": 35.30},
                {"month": "2024-12", "value": 35.80, "forecast": 35.40},
                {"month": "2025-01", "value": 35.95, "forecast": 35.50},
                {"month": "2025-02", "value": 36.10, "forecast": 35.60},
                {"month": "2025-03", "value": 36.25, "forecast": 35.70},
                {"month": "2025-04", "value": 36.40, "forecast": 35.80},
                {"month": "2025-05", "value": 36.30, "forecast": 35.90},
                {"month": "2025-06", "value": 36.30, "forecast": 36.00},
                {"month": "2025-07", "value": 36.42, "forecast": 36.10},
                {"month": "2025-08", "value": 36.50, "forecast": 36.45}
            ]
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
        # 州別雇用状況データ
        "state_data": {
            "CA": {"unemployment": 4.8, "employment_change": -0.2, "color": "high"},
            "TX": {"unemployment": 4.1, "employment_change": 0.3, "color": "medium"},
            "FL": {"unemployment": 3.9, "employment_change": 0.1, "color": "low"},
            "NY": {"unemployment": 4.5, "employment_change": -0.1, "color": "high"},
            "PA": {"unemployment": 4.2, "employment_change": 0.0, "color": "medium"},
            "IL": {"unemployment": 4.6, "employment_change": -0.2, "color": "high"},
            "OH": {"unemployment": 4.0, "employment_change": 0.1, "color": "medium"},
            "GA": {"unemployment": 3.8, "employment_change": 0.2, "color": "low"},
            "NC": {"unemployment": 3.7, "employment_change": 0.2, "color": "low"},
            "MI": {"unemployment": 4.3, "employment_change": 0.0, "color": "medium"},
            "NJ": {"unemployment": 4.4, "employment_change": -0.1, "color": "medium"},
            "VA": {"unemployment": 3.9, "employment_change": 0.1, "color": "low"},
            "WA": {"unemployment": 4.7, "employment_change": -0.1, "color": "high"},
            "AZ": {"unemployment": 4.2, "employment_change": 0.1, "color": "medium"},
            "MA": {"unemployment": 4.1, "employment_change": 0.0, "color": "medium"},
            "TN": {"unemployment": 3.6, "employment_change": 0.2, "color": "low"},
            "IN": {"unemployment": 3.8, "employment_change": 0.1, "color": "low"},
            "MO": {"unemployment": 3.9, "employment_change": 0.0, "color": "low"},
            "MD": {"unemployment": 4.0, "employment_change": 0.0, "color": "medium"},
            "WI": {"unemployment": 3.7, "employment_change": 0.1, "color": "low"}
        },
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

def create_complete_html_report():
    """グラフと州別データを含む完全なHTMLレポートを作成"""
    
    # 完全なデータを取得
    data = get_complete_employment_data()
    
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
  <title>米国雇用統計レポート — 2025年8月分（完全版）</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
    .container{{max-width:1200px;margin:auto;padding:24px}}

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

    .chart-container{{
      position:relative;
      height:300px;
      margin:20px 0;
    }}

    .kpi{{font-size:22px;font-weight:bold;margin-bottom:6px}}
    .up{{color:var(--pos)}}.down{{color:var(--neg)}}.warn{{color:var(--warn)}}
    .note{{font-size:12px;color:var(--muted)}}

    .us-map{{
      display:grid;
      grid-template-columns:repeat(10,1fr);
      gap:2px;
      margin-top:12px;
    }}
    .state{{
      aspect-ratio:1;
      display:flex;
      align-items:center;
      justify-content:center;
      font-size:10px;
      border:1px solid var(--border);
      cursor:pointer;
      transition:all 0.2s;
    }}
    .state:hover{{
      transform:scale(1.1);
      z-index:10;
      position:relative;
    }}
    .state.low{{background:#d4edda;color:#155724}}
    .state.medium{{background:#fff3cd;color:#856404}}
    .state.high{{background:#f8d7da;color:#721c24}}
    
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
    
    .state-tooltip{{
      position:absolute;
      background:var(--panel);
      border:1px solid var(--border);
      padding:8px;
      border-radius:4px;
      font-size:12px;
      pointer-events:none;
      z-index:1000;
      display:none;
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
      <div class="chart-container">
        <canvas id="nfpChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>失業率 / 参加率</h2>
      <div class="kpi {ur_class}">{data["indicators"]["unemployment_rate"]["actual"]}% / {data["indicators"]["labor_force_participation"]["actual"]}%</div>
      <div class="chart-container">
        <canvas id="unemploymentChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>平均時給</h2>
      <div class="kpi">${data["indicators"]["average_hourly_earnings"]["actual"]} (+{data["indicators"]["average_hourly_earnings_yoy"]["actual"]}% YoY)</div>
      <div class="chart-container">
        <canvas id="wageChart"></canvas>
      </div>
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
    <div class="chart-container">
      <canvas id="sectorChart"></canvas>
    </div>
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

  <!-- 州別雇用状況 -->
  <div class="card">
    <h2>州別雇用状況</h2>
    <p class="note">失業率: 緑=低い(3.5-4.0%), 黄=中程度(4.0-4.5%), 赤=高い(4.5%以上)</p>
    <div class="us-map" id="stateMap">
"""
    
    # 州別データを追加
    state_order = ["WA", "OR", "CA", "NV", "ID", "UT", "AZ", "CO", "NM", "TX", 
                   "OK", "KS", "NE", "SD", "ND", "MT", "WY", "HI", "AK", "MN", 
                   "IA", "MO", "AR", "LA", "MS", "AL", "TN", "KY", "IN", "IL", 
                   "WI", "MI", "OH", "PA", "NY", "VT", "NH", "ME", "MA", "RI", 
                   "CT", "NJ", "DE", "MD", "DC", "VA", "WV", "NC", "SC", "GA", "FL"]
    
    for state in state_order:
        if state in data["state_data"]:
            state_info = data["state_data"][state]
            html_content += f"""
      <div class="state {state_info['color']}" 
           data-state="{state}" 
           data-unemployment="{state_info['unemployment']}" 
           data-employment-change="{state_info['employment_change']}"
           title="{state}: 失業率{state_info['unemployment']}%, 雇用変化{state_info['employment_change']:+.1f}%">
        {state}
      </div>
"""
        else:
            html_content += f"""
      <div class="state" title="{state}: データなし">
        {state}
      </div>
"""
    
    html_content += f"""
    </div>
    <div class="state-tooltip" id="stateTooltip"></div>
    <p class="note">実際はGeoJSON＋ECharts等で描画推奨</p>
  </div>

  <!-- 市場反応 -->
  <section class="grid cols-3">
    <div class="card">
      <h2>株式</h2>
      <div class="chart-container">
        <canvas id="stockChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>債券</h2>
      <div class="chart-container">
        <canvas id="bondChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>為替</h2>
      <div class="chart-container">
        <canvas id="currencyChart"></canvas>
      </div>
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

<script>
// チャートデータ
const chartData = {json.dumps(data["chart_data"], ensure_ascii=False)};
const stateData = {json.dumps(data["state_data"], ensure_ascii=False)};

// NFPチャート
const nfpCtx = document.getElementById('nfpChart').getContext('2d');
new Chart(nfpCtx, {{
    type: 'line',
    data: {{
        labels: chartData.nfp_trend.map(d => d.month),
        datasets: [{{
            label: '実際値',
            data: chartData.nfp_trend.map(d => d.value),
            borderColor: '#007bff',
            backgroundColor: 'rgba(0, 123, 255, 0.1)',
            tension: 0.1,
            fill: true
        }}, {{
            label: '予想値',
            data: chartData.nfp_trend.map(d => d.forecast),
            borderColor: '#dc3545',
            backgroundColor: 'rgba(220, 53, 69, 0.1)',
            borderDash: [5, 5],
            tension: 0.1
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            title: {{
                display: true,
                text: 'NFP推移（千人）'
            }}
        }},
        scales: {{
            y: {{
                beginAtZero: false,
                title: {{
                    display: true,
                    text: '千人'
                }}
            }}
        }}
    }}
}});

// 失業率チャート
const urCtx = document.getElementById('unemploymentChart').getContext('2d');
new Chart(urCtx, {{
    type: 'line',
    data: {{
        labels: chartData.unemployment_trend.map(d => d.month),
        datasets: [{{
            label: '実際値',
            data: chartData.unemployment_trend.map(d => d.value),
            borderColor: '#dc3545',
            backgroundColor: 'rgba(220, 53, 69, 0.1)',
            tension: 0.1,
            fill: true
        }}, {{
            label: '予想値',
            data: chartData.unemployment_trend.map(d => d.forecast),
            borderColor: '#6c757d',
            backgroundColor: 'rgba(108, 117, 125, 0.1)',
            borderDash: [5, 5],
            tension: 0.1
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            title: {{
                display: true,
                text: '失業率推移（%）'
            }}
        }},
        scales: {{
            y: {{
                beginAtZero: false,
                title: {{
                    display: true,
                    text: '%'
                }}
            }}
        }}
    }}
}});

// 賃金チャート
const wageCtx = document.getElementById('wageChart').getContext('2d');
new Chart(wageCtx, {{
    type: 'line',
    data: {{
        labels: chartData.wage_trend.map(d => d.month),
        datasets: [{{
            label: '実際値',
            data: chartData.wage_trend.map(d => d.value),
            borderColor: '#28a745',
            backgroundColor: 'rgba(40, 167, 69, 0.1)',
            tension: 0.1,
            fill: true
        }}, {{
            label: '予想値',
            data: chartData.wage_trend.map(d => d.forecast),
            borderColor: '#6c757d',
            backgroundColor: 'rgba(108, 117, 125, 0.1)',
            borderDash: [5, 5],
            tension: 0.1
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            title: {{
                display: true,
                text: '平均時給推移（ドル）'
            }}
        }},
        scales: {{
            y: {{
                beginAtZero: false,
                title: {{
                    display: true,
                    text: 'ドル'
                }}
            }}
        }}
    }}
}});

// セクターチャート
const sectorCtx = document.getElementById('sectorChart').getContext('2d');
const sectorData = {json.dumps(data["sector_data"], ensure_ascii=False)};
new Chart(sectorCtx, {{
    type: 'bar',
    data: {{
        labels: sectorData.map(s => s.sector),
        datasets: [{{
            label: '雇用増減（千人）',
            data: sectorData.map(s => s.change),
            backgroundColor: sectorData.map(s => s.change >= 0 ? '#28a745' : '#dc3545'),
            borderColor: sectorData.map(s => s.change >= 0 ? '#1e7e34' : '#c82333'),
            borderWidth: 1
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            title: {{
                display: true,
                text: 'セクター別雇用増減（千人）'
            }}
        }},
        scales: {{
            y: {{
                beginAtZero: true,
                title: {{
                    display: true,
                    text: '千人'
                }}
            }}
        }}
    }}
}});

// 市場反応チャート
const stockCtx = document.getElementById('stockChart').getContext('2d');
new Chart(stockCtx, {{
    type: 'bar',
    data: {{
        labels: ['S&P500', 'Nasdaq', 'Dow'],
        datasets: [{{
            label: '変化率（%）',
            data: [0.26, 0.15, 0.26],
            backgroundColor: ['#28a745', '#28a745', '#28a745']
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            title: {{
                display: true,
                text: '株式市場反応（%）'
            }}
        }}
    }}
}});

const bondCtx = document.getElementById('bondChart').getContext('2d');
new Chart(bondCtx, {{
    type: 'bar',
    data: {{
        labels: ['10年債', '2年債'],
        datasets: [{{
            label: '利回り変化（%）',
            data: [-0.05, -0.03],
            backgroundColor: ['#dc3545', '#dc3545']
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            title: {{
                display: true,
                text: '債券市場反応（%）'
            }}
        }}
    }}
}});

const currencyCtx = document.getElementById('currencyChart').getContext('2d');
new Chart(currencyCtx, {{
    type: 'bar',
    data: {{
        labels: ['USD/JPY', 'DXY'],
        datasets: [{{
            label: '変化率（%）',
            data: [-0.3, -0.2],
            backgroundColor: ['#dc3545', '#dc3545']
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            title: {{
                display: true,
                text: '為替市場反応（%）'
            }}
        }}
    }}
}});

// 州別ツールチップ
const stateMap = document.getElementById('stateMap');
const tooltip = document.getElementById('stateTooltip');

stateMap.addEventListener('mouseover', function(e) {{
    if (e.target.classList.contains('state') && e.target.dataset.state) {{
        const state = e.target.dataset.state;
        const unemployment = e.target.dataset.unemployment;
        const employmentChange = e.target.dataset.employmentChange;
        
        tooltip.innerHTML = `
            <strong>${{state}}</strong><br/>
            失業率: ${{unemployment}}%<br/>
            雇用変化: ${{employmentChange}}%
        `;
        tooltip.style.display = 'block';
        tooltip.style.left = e.pageX + 10 + 'px';
        tooltip.style.top = e.pageY - 10 + 'px';
    }}
}});

stateMap.addEventListener('mouseout', function(e) {{
    if (e.target.classList.contains('state')) {{
        tooltip.style.display = 'none';
    }}
}});

stateMap.addEventListener('mousemove', function(e) {{
    if (e.target.classList.contains('state') && e.target.dataset.state) {{
        tooltip.style.left = e.pageX + 10 + 'px';
        tooltip.style.top = e.pageY - 10 + 'px';
    }}
}});
</script>
</body>
</html>
"""
    
    return html_content

def main():
    """メイン実行関数"""
    
    try:
        print("🚀 グラフと州別データを含む完全な雇用統計レポート生成を開始します...")
        
        # 出力ディレクトリを設定
        output_dir = Path("test_output/enhanced_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # HTMLレポートを生成
        html_content = create_complete_html_report()
        
        # ファイル名生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = output_dir / f"complete_employment_report_aug2025_{timestamp}.html"
        
        # HTMLファイルを保存
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("✅ 完全な雇用統計レポート生成が完了しました！")
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
