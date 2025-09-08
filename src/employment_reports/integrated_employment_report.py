#!/usr/bin/env python3
"""
Integrated Employment Report with Folium Map
Folium地図を統合した雇用統計レポート
"""

import folium
import json
import requests
from pathlib import Path
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def get_real_us_geojson():
    """実際の米国州のGeoJSONデータを取得"""
    url = "https://raw.githubusercontent.com/python-visualization/folium/main/examples/data/us-states.json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"GeoJSONデータの取得に失敗しました: {e}")
        return None

def get_leading_indicators_data():
    """先行指標・関連指標データを取得（ミニグラフ用データ含む）"""
    return {
        "jolts": {
            "job_openings": {"current": 8.1, "previous": 8.2, "unit": "百万件", "trend": [8.5, 8.3, 8.2, 8.1]},
            "hires": {"current": 5.7, "previous": 5.8, "unit": "百万件", "trend": [6.0, 5.9, 5.8, 5.7]},
            "quits": {"current": 3.4, "previous": 3.5, "unit": "百万件", "trend": [3.6, 3.5, 3.5, 3.4]},
            "layoffs": {"current": 1.6, "previous": 1.5, "unit": "百万件", "trend": [1.4, 1.4, 1.5, 1.6]}
        },
        "adp": {"current": 15, "previous": 18, "forecast": 20, "unit": "千人", "trend": [25, 22, 18, 15]},
        "ism_employment": {"current": 48.2, "previous": 49.4, "forecast": 50.0, "unit": "指数", "trend": [51.2, 50.1, 49.4, 48.2]},
        "challenger_job_cuts": {"current": 45.2, "previous": 38.8, "unit": "千人", "trend": [30.5, 35.2, 38.8, 45.2]},
        "weekly_claims": {"current": 215, "previous": 210, "forecast": 220, "unit": "千人", "trend": [200, 205, 210, 215]},
        "nfib_labor_shortage": {"current": 42, "previous": 45, "unit": "%", "trend": [48, 46, 45, 42]}
    }

def get_employment_data():
    """雇用統計データを取得（全50州、zスコア付き）"""
    return {
        # 主要州（失業率、雇用変化、NFP変化、過去12ヶ月平均、標準偏差、zスコア）
        "California": {"unemployment": 4.8, "employment_change": -0.2, "nfp_change": -15.2, 
                      "avg_12m": 4.2, "std_12m": 0.3, "z_score": 2.0},
        "Texas": {"unemployment": 4.1, "employment_change": 0.3, "nfp_change": 8.5, 
                 "avg_12m": 4.0, "std_12m": 0.2, "z_score": 0.5},
        "Florida": {"unemployment": 3.9, "employment_change": 0.1, "nfp_change": 5.2, 
                   "avg_12m": 3.8, "std_12m": 0.2, "z_score": 0.5},
        "New York": {"unemployment": 4.5, "employment_change": -0.1, "nfp_change": -3.8, 
                    "avg_12m": 4.1, "std_12m": 0.3, "z_score": 1.3},
        "Pennsylvania": {"unemployment": 4.2, "employment_change": 0.0, "nfp_change": 1.2, 
                        "avg_12m": 4.0, "std_12m": 0.2, "z_score": 1.0},
        "Illinois": {"unemployment": 4.6, "employment_change": -0.2, "nfp_change": -8.9, 
                    "avg_12m": 4.2, "std_12m": 0.3, "z_score": 1.3},
        "Ohio": {"unemployment": 4.0, "employment_change": 0.1, "nfp_change": 2.1, 
                "avg_12m": 3.9, "std_12m": 0.2, "z_score": 0.5},
        "Georgia": {"unemployment": 3.8, "employment_change": 0.2, "nfp_change": 6.8, 
                   "avg_12m": 3.7, "std_12m": 0.2, "z_score": 0.5},
        "North Carolina": {"unemployment": 3.7, "employment_change": 0.2, "nfp_change": 7.3, 
                          "avg_12m": 3.6, "std_12m": 0.2, "z_score": 0.5},
        "Michigan": {"unemployment": 4.3, "employment_change": 0.0, "nfp_change": -1.5, 
                    "avg_12m": 4.0, "std_12m": 0.3, "z_score": 1.0},
        "New Jersey": {"unemployment": 4.4, "employment_change": -0.1, "nfp_change": -2.1, 
                      "avg_12m": 4.1, "std_12m": 0.2, "z_score": 1.5},
        "Virginia": {"unemployment": 3.9, "employment_change": 0.1, "nfp_change": 3.4, 
                    "avg_12m": 3.8, "std_12m": 0.2, "z_score": 0.5},
        "Washington": {"unemployment": 4.7, "employment_change": -0.1, "nfp_change": -4.2, 
                      "avg_12m": 4.2, "std_12m": 0.3, "z_score": 1.7},
        "Arizona": {"unemployment": 4.2, "employment_change": 0.1, "nfp_change": 2.8, 
                   "avg_12m": 4.0, "std_12m": 0.2, "z_score": 1.0},
        "Massachusetts": {"unemployment": 4.1, "employment_change": 0.0, "nfp_change": 0.8, 
                         "avg_12m": 3.9, "std_12m": 0.2, "z_score": 1.0},
        "Tennessee": {"unemployment": 3.6, "employment_change": 0.2, "nfp_change": 4.1, 
                     "avg_12m": 3.5, "std_12m": 0.2, "z_score": 0.5},
        "Indiana": {"unemployment": 3.8, "employment_change": 0.1, "nfp_change": 2.9, 
                   "avg_12m": 3.7, "std_12m": 0.2, "z_score": 0.5},
        "Missouri": {"unemployment": 3.9, "employment_change": 0.0, "nfp_change": 1.7, 
                    "avg_12m": 3.8, "std_12m": 0.2, "z_score": 0.5},
        "Maryland": {"unemployment": 4.0, "employment_change": 0.0, "nfp_change": 1.3, 
                    "avg_12m": 3.9, "std_12m": 0.2, "z_score": 0.5},
        "Wisconsin": {"unemployment": 3.7, "employment_change": 0.1, "nfp_change": 2.4, 
                     "avg_12m": 3.6, "std_12m": 0.2, "z_score": 0.5},
        
        # 追加の州
        "Colorado": {"unemployment": 3.9, "employment_change": 0.1, "nfp_change": 3.2, 
                    "avg_12m": 3.8, "std_12m": 0.2, "z_score": 0.5},
        "Minnesota": {"unemployment": 3.5, "employment_change": 0.2, "nfp_change": 4.5, 
                     "avg_12m": 3.4, "std_12m": 0.2, "z_score": 0.5},
        "South Carolina": {"unemployment": 3.6, "employment_change": 0.2, "nfp_change": 3.8, 
                          "avg_12m": 3.5, "std_12m": 0.2, "z_score": 0.5},
        "Alabama": {"unemployment": 3.8, "employment_change": 0.1, "nfp_change": 2.1, 
                   "avg_12m": 3.7, "std_12m": 0.2, "z_score": 0.5},
        "Louisiana": {"unemployment": 4.1, "employment_change": 0.0, "nfp_change": 1.5, 
                     "avg_12m": 4.0, "std_12m": 0.2, "z_score": 0.5},
        "Kentucky": {"unemployment": 3.9, "employment_change": 0.1, "nfp_change": 2.3, 
                    "avg_12m": 3.8, "std_12m": 0.2, "z_score": 0.5},
        "Oregon": {"unemployment": 4.3, "employment_change": -0.1, "nfp_change": -2.1, 
                  "avg_12m": 4.0, "std_12m": 0.3, "z_score": 1.0},
        "Oklahoma": {"unemployment": 3.7, "employment_change": 0.1, "nfp_change": 2.8, 
                    "avg_12m": 3.6, "std_12m": 0.2, "z_score": 0.5},
        "Connecticut": {"unemployment": 4.2, "employment_change": 0.0, "nfp_change": 0.8, 
                       "avg_12m": 4.0, "std_12m": 0.2, "z_score": 1.0},
        "Utah": {"unemployment": 3.4, "employment_change": 0.2, "nfp_change": 3.5, 
                "avg_12m": 3.3, "std_12m": 0.2, "z_score": 0.5},
        "Iowa": {"unemployment": 3.6, "employment_change": 0.1, "nfp_change": 2.2, 
                "avg_12m": 3.5, "std_12m": 0.2, "z_score": 0.5},
        "Nevada": {"unemployment": 4.4, "employment_change": -0.1, "nfp_change": -1.8, 
                  "avg_12m": 4.1, "std_12m": 0.3, "z_score": 1.0},
        "Arkansas": {"unemployment": 3.8, "employment_change": 0.1, "nfp_change": 1.9, 
                    "avg_12m": 3.7, "std_12m": 0.2, "z_score": 0.5},
        "Mississippi": {"unemployment": 4.0, "employment_change": 0.0, "nfp_change": 1.2, 
                       "avg_12m": 3.9, "std_12m": 0.2, "z_score": 0.5},
        "Kansas": {"unemployment": 3.7, "employment_change": 0.1, "nfp_change": 2.1, 
                  "avg_12m": 3.6, "std_12m": 0.2, "z_score": 0.5},
        "New Mexico": {"unemployment": 4.2, "employment_change": 0.0, "nfp_change": 1.4, 
                      "avg_12m": 4.0, "std_12m": 0.2, "z_score": 1.0},
        "Nebraska": {"unemployment": 3.5, "employment_change": 0.1, "nfp_change": 1.8, 
                    "avg_12m": 3.4, "std_12m": 0.2, "z_score": 0.5},
        "West Virginia": {"unemployment": 4.1, "employment_change": 0.0, "nfp_change": 0.9, 
                         "avg_12m": 4.0, "std_12m": 0.2, "z_score": 0.5},
        "Idaho": {"unemployment": 3.6, "employment_change": 0.1, "nfp_change": 2.3, 
                 "avg_12m": 3.5, "std_12m": 0.2, "z_score": 0.5},
        "Hawaii": {"unemployment": 4.3, "employment_change": -0.1, "nfp_change": -1.2, 
                  "avg_12m": 4.0, "std_12m": 0.3, "z_score": 1.0},
        "New Hampshire": {"unemployment": 4.0, "employment_change": 0.0, "nfp_change": 1.1, 
                         "avg_12m": 3.9, "std_12m": 0.2, "z_score": 0.5},
        "Maine": {"unemployment": 4.1, "employment_change": 0.0, "nfp_change": 0.8, 
                 "avg_12m": 4.0, "std_12m": 0.2, "z_score": 0.5},
        "Montana": {"unemployment": 3.8, "employment_change": 0.1, "nfp_change": 1.5, 
                   "avg_12m": 3.7, "std_12m": 0.2, "z_score": 0.5},
        "Rhode Island": {"unemployment": 4.2, "employment_change": 0.0, "nfp_change": 0.7, 
                        "avg_12m": 4.0, "std_12m": 0.2, "z_score": 1.0},
        "Delaware": {"unemployment": 4.0, "employment_change": 0.0, "nfp_change": 1.0, 
                    "avg_12m": 3.9, "std_12m": 0.2, "z_score": 0.5},
        "South Dakota": {"unemployment": 3.4, "employment_change": 0.1, "nfp_change": 1.3, 
                        "avg_12m": 3.3, "std_12m": 0.2, "z_score": 0.5},
        "North Dakota": {"unemployment": 3.6, "employment_change": 0.1, "nfp_change": 1.4, 
                        "avg_12m": 3.5, "std_12m": 0.2, "z_score": 0.5},
        "Alaska": {"unemployment": 4.5, "employment_change": -0.1, "nfp_change": -0.8, 
                  "avg_12m": 4.2, "std_12m": 0.3, "z_score": 1.0},
        "Vermont": {"unemployment": 4.1, "employment_change": 0.0, "nfp_change": 0.6, 
                   "avg_12m": 4.0, "std_12m": 0.2, "z_score": 0.5},
        "Wyoming": {"unemployment": 3.7, "employment_change": 0.1, "nfp_change": 1.2, 
                   "avg_12m": 3.6, "std_12m": 0.2, "z_score": 0.5}
    }

def create_folium_map():
    """Folium地図を作成"""
    geojson_data = get_real_us_geojson()
    if not geojson_data:
        return None
    
    employment_data = get_employment_data()
    
    # 地図の中心点
    center_lat, center_lon = 39.8283, -98.5795
    
    # Folium地図を作成
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles='OpenStreetMap'
    )
    
    # zスコアに基づく色分け関数（過去トレンドからの変化）
    def get_color(z_score):
        if z_score <= -1.0:
            return '#2E8B57'  # 緑（大幅改善）
        elif z_score <= -0.5:
            return '#90EE90'  # 薄緑（改善）
        elif z_score <= 0.5:
            return '#FFD700'  # 黄（正常範囲）
        elif z_score <= 1.0:
            return '#FF8C00'  # オレンジ（悪化）
        else:
            return '#DC143C'  # 赤（大幅悪化）
    
    # 各州にデータを追加
    for feature in geojson_data['features']:
        state_name = feature['properties']['name']
        
        if state_name in employment_data:
            data = employment_data[state_name]
            unemployment = data['unemployment']
            employment_change = data['employment_change']
            nfp_change = data['nfp_change']
            z_score = data['z_score']
            avg_12m = data['avg_12m']
            
            # ポップアップ用のHTML
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; width: 220px;">
                <h4 style="margin: 0 0 10px 0; color: #333;">{state_name}</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;"><strong>現在の失業率:</strong></td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd; text-align: right;">{unemployment}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;"><strong>12ヶ月平均:</strong></td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd; text-align: right;">{avg_12m}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;"><strong>Zスコア:</strong></td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd; text-align: right;">{z_score:+.1f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;"><strong>雇用変化:</strong></td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd; text-align: right;">{employment_change:+.1f}%</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px;"><strong>NFP変化:</strong></td>
                        <td style="padding: 5px; text-align: right;">{nfp_change:+.1f}千人</td>
                    </tr>
                </table>
            </div>
            """
            
            # 州の境界線を追加
            folium.GeoJson(
                feature,
                style_function=lambda x, z_score=z_score: {
                    'fillColor': get_color(z_score),
                    'color': 'white',
                    'weight': 2,
                    'fillOpacity': 0.7
                },
                popup=folium.Popup(popup_html, max_width=270),
                tooltip=f"{state_name}: Zスコア {z_score:+.1f} (失業率 {unemployment}%)"
            ).add_to(m)
    
    return m

def create_integrated_html_report():
    """Folium地図を統合したHTMLレポートを作成"""
    
    # Folium地図を作成
    folium_map = create_folium_map()
    if not folium_map:
        print("❌ 地図の作成に失敗しました")
        return None
    
    # 地図をHTML文字列として取得
    map_html = folium_map._repr_html_()
    
    # メインのHTMLレポートを作成
    html_content = f"""
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>米国雇用統計レポート — 2025年8月分（統合版）</title>
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

    .map-container{{
      margin:20px 0;
      border:1px solid var(--border);
      border-radius:4px;
      overflow:hidden;
    }}

    .map-container iframe{{
      width:100%;
      height:500px;
      border:none;
    }}

    .leading-indicators{{
      display:grid;
      grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));
      gap:15px;
      margin-top:15px;
    }}
    
    .indicator-card{{
      background:#f8f9fa;
      border:1px solid var(--border);
      padding:15px;
      text-align:center;
    }}
    
    .indicator-value{{
      font-size:24px;
      font-weight:bold;
      margin-bottom:5px;
    }}
    
    .indicator-label{{
      font-size:12px;
      color:var(--muted);
    }}
    
    .mini-chart{{
      height:60px;
      margin-top:8px;
    }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>米国雇用統計レポート <span id="month">2025年8月</span></h1>
    <div class="meta">Source: BLS | Release: <span id="release-date">2025-09-05</span> | 2020年以来最低の雇用増加</div>
  </header>

  <!-- 重要なアラート -->
  <div class="alert-box negative">
    <strong>⚠️ 重要なポイント:</strong> 8月の雇用増加は22,000人と2020年以来最低水準。市場予想75,000人を大幅に下回る結果となりました。
  </div>

  <!-- KPI -->
  <section class="grid cols-3">
    <div class="card">
      <h2>NFP</h2>
      <div class="kpi down">+22千人</div>
      <div class="chart-container">
        <canvas id="nfpChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>失業率 / 参加率</h2>
      <div class="kpi warn">4.3% / 62.7%</div>
      <div class="chart-container">
        <canvas id="unemploymentChart"></canvas>
      </div>
    </div>
    <div class="card">
      <h2>平均時給（前年比）</h2>
      <div class="kpi">+3.8% YoY</div>
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
        <tr><td>NFP</td><td>+22</td><td>+75</td><td>+79</td><td class="down">大幅下振れ</td></tr>
        <tr><td>失業率</td><td>4.3%</td><td>4.2%</td><td>4.2%</td><td class="warn">上昇</td></tr>
        <tr><td>平均時給 YoY</td><td>+3.8%</td><td>+3.9%</td><td>+4.0%</td><td>鈍化</td></tr>
      </tbody>
    </table>
  </div>

  <!-- 先行指標・関連指標 -->
  <div class="card">
    <h2>先行指標・関連指標</h2>
    <div class="leading-indicators">
      <div class="indicator-card">
        <div class="indicator-value">8.1</div>
        <div class="indicator-label">JOLTS求人数（百万件）</div>
        <div class="mini-chart">
          <canvas id="joltsOpeningsChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">5.7</div>
        <div class="indicator-label">JOLTS採用数（百万件）</div>
        <div class="mini-chart">
          <canvas id="joltsHiresChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">3.4</div>
        <div class="indicator-label">JOLTS離職数（百万件）</div>
        <div class="mini-chart">
          <canvas id="joltsQuitsChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">15</div>
        <div class="indicator-label">ADP雇用（千人）</div>
        <div class="mini-chart">
          <canvas id="adpChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">48.2</div>
        <div class="indicator-label">ISM雇用指数</div>
        <div class="mini-chart">
          <canvas id="ismChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">45.2</div>
        <div class="indicator-label">Challenger解雇（千人）</div>
        <div class="mini-chart">
          <canvas id="challengerChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">215</div>
        <div class="indicator-label">週次失業保険申請（千人）</div>
        <div class="mini-chart">
          <canvas id="claimsChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">42</div>
        <div class="indicator-label">NFIB労働力不足（%）</div>
        <div class="mini-chart">
          <canvas id="nfibChart"></canvas>
        </div>
      </div>
    </div>
  </div>

  <!-- 州別雇用状況（Folium地図） -->
  <div class="card">
    <h2>州別雇用状況（Zスコア分析）</h2>
    <p class="note">過去12ヶ月のトレンドからの変化: 緑=大幅改善(Z≤-1.0), 薄緑=改善(-1.0<Z≤-0.5), 黄=正常(-0.5<Z≤0.5), オレンジ=悪化(0.5<Z≤1.0), 赤=大幅悪化(Z>1.0)</p>
    <div class="map-container">
      {map_html}
    </div>
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
        <tr><td>ヘルスケア</td><td>+58.6</td><td>+0.3pt</td></tr>
        <tr><td>建設業</td><td>+15.0</td><td>+0.1pt</td></tr>
        <tr><td>小売業</td><td>+2.4</td><td>+0.0pt</td></tr>
        <tr><td>政府</td><td>+8.0</td><td>+0.0pt</td></tr>
        <tr><td>製造業</td><td class="down">-7.0</td><td>-0.0pt</td></tr>
        <tr><td>卸売業</td><td class="down">-6.6</td><td>-0.0pt</td></tr>
        <tr><td>専門サービス</td><td class="down">-5.0</td><td>-0.0pt</td></tr>
        <tr><td>運輸・倉庫</td><td class="down">-3.0</td><td>-0.0pt</td></tr>
      </tbody>
    </table>
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
const chartData = {{
    "nfp_trend": [
        {{"month": "2024-08", "value": 150, "avg3m": 180}},
        {{"month": "2024-09", "value": 297, "avg3m": 200}},
        {{"month": "2024-10", "value": 150, "avg3m": 199}},
        {{"month": "2024-11", "value": 199, "avg3m": 215}},
        {{"month": "2024-12", "value": 216, "avg3m": 188}},
        {{"month": "2025-01", "value": 229, "avg3m": 215}},
        {{"month": "2025-02", "value": 151, "avg3m": 199}},
        {{"month": "2025-03", "value": 175, "avg3m": 185}},
        {{"month": "2025-04", "value": 175, "avg3m": 167}},
        {{"month": "2025-05", "value": 140, "avg3m": 163}},
        {{"month": "2025-06", "value": 147, "avg3m": 154}},
        {{"month": "2025-07", "value": 73, "avg3m": 120}},
        {{"month": "2025-08", "value": 22, "avg3m": 81}}
    ],
    "unemployment_trend": [
        {{"month": "2024-08", "u3": 3.8, "u6": 7.0}},
        {{"month": "2024-09", "u3": 3.8, "u6": 7.0}},
        {{"month": "2024-10", "u3": 3.9, "u6": 7.2}},
        {{"month": "2024-11", "u3": 3.7, "u6": 7.0}},
        {{"month": "2024-12", "u3": 3.7, "u6": 7.1}},
        {{"month": "2025-01", "u3": 3.7, "u6": 7.2}},
        {{"month": "2025-02", "u3": 3.9, "u6": 7.4}},
        {{"month": "2025-03", "u3": 3.8, "u6": 7.3}},
        {{"month": "2025-04", "u3": 3.9, "u6": 7.5}},
        {{"month": "2025-05", "u3": 4.0, "u6": 7.6}},
        {{"month": "2025-06", "u3": 4.1, "u6": 7.7}},
        {{"month": "2025-07", "u3": 4.2, "u6": 7.6}},
        {{"month": "2025-08", "u3": 4.3, "u6": 7.8}}
    ],
    "wage_yoy_trend": [
        {{"month": "2024-08", "yoy": 4.2}},
        {{"month": "2024-09", "yoy": 4.1}},
        {{"month": "2024-10", "yoy": 4.0}},
        {{"month": "2024-11", "yoy": 4.1}},
        {{"month": "2024-12", "yoy": 4.0}},
        {{"month": "2025-01", "yoy": 4.0}},
        {{"month": "2025-02", "yoy": 4.0}},
        {{"month": "2025-03", "yoy": 4.0}},
        {{"month": "2025-04", "yoy": 3.9}},
        {{"month": "2025-05", "yoy": 3.9}},
        {{"month": "2025-06", "yoy": 3.9}},
        {{"month": "2025-07", "yoy": 4.0}},
        {{"month": "2025-08", "yoy": 3.8}}
    ]
}};

// NFPチャート（棒グラフ + 3ヶ月平均折れ線）
const nfpCtx = document.getElementById('nfpChart').getContext('2d');
new Chart(nfpCtx, {{
    type: 'bar',
    data: {{
        labels: chartData.nfp_trend.map(d => d.month),
        datasets: [{{
            label: 'NFP（千人）',
            type: 'bar',
            data: chartData.nfp_trend.map(d => d.value),
            backgroundColor: 'rgba(0, 123, 255, 0.7)',
            borderColor: '#007bff',
            borderWidth: 1
        }}, {{
            label: '3ヶ月平均',
            type: 'line',
            data: chartData.nfp_trend.map(d => d.avg3m),
            borderColor: '#dc3545',
            backgroundColor: 'rgba(220, 53, 69, 0.1)',
            borderWidth: 2,
            fill: false,
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

// 失業率チャート（U3 + U6、2軸表示）
const urCtx = document.getElementById('unemploymentChart').getContext('2d');
new Chart(urCtx, {{
    type: 'line',
    data: {{
        labels: chartData.unemployment_trend.map(d => d.month),
        datasets: [{{
            label: 'U-3失業率（%）',
            data: chartData.unemployment_trend.map(d => d.u3),
            borderColor: '#dc3545',
            backgroundColor: 'rgba(220, 53, 69, 0.1)',
            tension: 0.1,
            fill: false,
            yAxisID: 'y'
        }}, {{
            label: 'U-6失業率（%）',
            data: chartData.unemployment_trend.map(d => d.u6),
            borderColor: '#ffc107',
            backgroundColor: 'rgba(255, 193, 7, 0.1)',
            tension: 0.1,
            fill: false,
            yAxisID: 'y1'
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
                type: 'linear',
                display: true,
                position: 'left',
                beginAtZero: false,
                title: {{
                    display: true,
                    text: 'U-3失業率（%）'
                }}
            }},
            y1: {{
                type: 'linear',
                display: true,
                position: 'right',
                beginAtZero: false,
                title: {{
                    display: true,
                    text: 'U-6失業率（%）'
                }},
                grid: {{
                    drawOnChartArea: false,
                }}
            }}
        }}
    }}
}});

// 賃金前年比チャート
const wageCtx = document.getElementById('wageChart').getContext('2d');
new Chart(wageCtx, {{
    type: 'line',
    data: {{
        labels: chartData.wage_yoy_trend.map(d => d.month),
        datasets: [{{
            label: '前年比（%）',
            data: chartData.wage_yoy_trend.map(d => d.yoy),
            borderColor: '#28a745',
            backgroundColor: 'rgba(40, 167, 69, 0.1)',
            tension: 0.1,
            fill: true
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            title: {{
                display: true,
                text: '平均時給前年比推移（%）'
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

// セクターチャート
const sectorCtx = document.getElementById('sectorChart').getContext('2d');
new Chart(sectorCtx, {{
    type: 'bar',
    data: {{
        labels: ['ヘルスケア', '建設業', '小売業', '政府', '製造業', '卸売業', '専門サービス', '運輸・倉庫'],
        datasets: [{{
            label: '雇用増減（千人）',
            data: [58.6, 15.0, 2.4, 8.0, -7.0, -6.6, -5.0, -3.0],
            backgroundColor: ['#28a745', '#28a745', '#28a745', '#28a745', '#dc3545', '#dc3545', '#dc3545', '#dc3545'],
            borderColor: ['#1e7e34', '#1e7e34', '#1e7e34', '#1e7e34', '#c82333', '#c82333', '#c82333', '#c82333'],
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
            label: '利回り変化（bp）',
            data: [-5, -3],
            backgroundColor: ['#dc3545', '#dc3545']
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            title: {{
                display: true,
                text: '債券市場反応（bp）'
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

// ミニグラフ作成関数
function createMiniChart(canvasId, data, color) {{
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {{
        type: 'line',
        data: {{
            labels: ['3ヶ月前', '2ヶ月前', '1ヶ月前', '今月'],
            datasets: [{{
                data: data,
                borderColor: color,
                backgroundColor: color + '20',
                borderWidth: 2,
                pointRadius: 3,
                pointHoverRadius: 5,
                tension: 0.1,
                fill: true
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{ display: false }},
                tooltip: {{ enabled: false }}
            }},
            scales: {{
                x: {{ display: false }},
                y: {{ display: false }}
            }},
            elements: {{
                point: {{
                    radius: 2
                }}
            }}
        }}
    }});
}}

// ミニグラフを作成
createMiniChart('joltsOpeningsChart', [8.5, 8.3, 8.2, 8.1], '#007bff');
createMiniChart('joltsHiresChart', [6.0, 5.9, 5.8, 5.7], '#28a745');
createMiniChart('joltsQuitsChart', [3.6, 3.5, 3.5, 3.4], '#ffc107');
createMiniChart('adpChart', [25, 22, 18, 15], '#17a2b8');
createMiniChart('ismChart', [51.2, 50.1, 49.4, 48.2], '#6f42c1');
createMiniChart('challengerChart', [30.5, 35.2, 38.8, 45.2], '#dc3545');
createMiniChart('claimsChart', [200, 205, 210, 215], '#fd7e14');
createMiniChart('nfibChart', [48, 46, 45, 42], '#20c997');
</script>
</body>
</html>
"""
    
    return html_content

def main():
    """メイン実行関数"""
    
    try:
        print("🗺️ Folium地図を統合した雇用統計レポート生成を開始します...")
        
        # 統合HTMLレポートを作成
        html_content = create_integrated_html_report()
        if not html_content:
            return None
        
        # 出力ディレクトリを作成
        output_dir = Path("test_output/enhanced_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # HTMLファイルを保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = output_dir / f"integrated_employment_report_{timestamp}.html"
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ 統合雇用統計レポートが生成されました: {html_file}")
        print(f"📁 生成されたファイル: {html_file}")
        print(f"🌐 HTMLレポート: {html_file}")
        print(f"   ブラウザで開くには: file://{os.path.abspath(html_file)}")
        
        # ブラウザで開く
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(html_file)}")
        print("🔍 ブラウザでレポートを開きました")
        
        return str(html_file)
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = main()
