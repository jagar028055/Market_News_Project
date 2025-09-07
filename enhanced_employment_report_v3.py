#!/usr/bin/env python3
"""
Enhanced Employment Report Generator with All Improvements
改善された雇用統計レポート生成（グラフ改善、先行指標、州別ヒートマップ含む）
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def get_enhanced_employment_data():
    """改善された雇用統計データを取得"""
    
    data = {
        "current_month": "2025年8月",
        "release_date": "2025-09-05",
        "indicators": {
            "nfp": {"actual": 22, "forecast": 75, "previous": 79, "revised": 73, "unit": "千人"},
            "unemployment_rate": {"actual": 4.3, "forecast": 4.2, "previous": 4.2, "unit": "%"},
            "labor_force_participation": {"actual": 62.7, "forecast": 62.6, "previous": 62.6, "unit": "%"},
            "average_hourly_earnings": {"actual": 36.50, "forecast": 36.45, "previous": 36.42, "unit": "ドル"},
            "average_hourly_earnings_yoy": {"actual": 3.8, "forecast": 3.9, "previous": 4.0, "unit": "%"}
        },
        # グラフ用データ（3ヶ月平均含む）
        "chart_data": {
            "nfp_trend": [
                {"month": "2024-08", "value": 150, "forecast": 170, "avg3m": 180},
                {"month": "2024-09", "value": 297, "forecast": 170, "avg3m": 200},
                {"month": "2024-10", "value": 150, "forecast": 180, "avg3m": 199},
                {"month": "2024-11", "value": 199, "forecast": 180, "avg3m": 215},
                {"month": "2024-12", "value": 216, "forecast": 170, "avg3m": 188},
                {"month": "2025-01", "value": 229, "forecast": 180, "avg3m": 215},
                {"month": "2025-02", "value": 151, "forecast": 200, "avg3m": 199},
                {"month": "2025-03", "value": 175, "forecast": 200, "avg3m": 185},
                {"month": "2025-04", "value": 175, "forecast": 240, "avg3m": 167},
                {"month": "2025-05", "value": 140, "forecast": 180, "avg3m": 163},
                {"month": "2025-06", "value": 147, "forecast": 190, "avg3m": 154},
                {"month": "2025-07", "value": 73, "forecast": 190, "avg3m": 120},
                {"month": "2025-08", "value": 22, "forecast": 75, "avg3m": 81}
            ],
            "unemployment_trend": [
                {"month": "2024-08", "u3": 3.8, "u6": 7.0, "forecast": 4.0},
                {"month": "2024-09", "u3": 3.8, "u6": 7.0, "forecast": 3.9},
                {"month": "2024-10", "u3": 3.9, "u6": 7.2, "forecast": 3.8},
                {"month": "2024-11", "u3": 3.7, "u6": 7.0, "forecast": 3.9},
                {"month": "2024-12", "u3": 3.7, "u6": 7.1, "forecast": 3.8},
                {"month": "2025-01", "u3": 3.7, "u6": 7.2, "forecast": 3.8},
                {"month": "2025-02", "u3": 3.9, "u6": 7.4, "forecast": 3.8},
                {"month": "2025-03", "u3": 3.8, "u6": 7.3, "forecast": 3.9},
                {"month": "2025-04", "u3": 3.9, "u6": 7.5, "forecast": 3.8},
                {"month": "2025-05", "u3": 4.0, "u6": 7.6, "forecast": 3.9},
                {"month": "2025-06", "u3": 4.1, "u6": 7.7, "forecast": 4.0},
                {"month": "2025-07", "u3": 4.2, "u6": 7.6, "forecast": 4.1},
                {"month": "2025-08", "u3": 4.3, "u6": 7.8, "forecast": 4.2}
            ],
            "wage_yoy_trend": [
                {"month": "2024-08", "yoy": 4.2, "forecast": 4.0},
                {"month": "2024-09", "yoy": 4.1, "forecast": 4.0},
                {"month": "2024-10", "yoy": 4.0, "forecast": 3.9},
                {"month": "2024-11", "yoy": 4.1, "forecast": 3.9},
                {"month": "2024-12", "yoy": 4.0, "forecast": 3.8},
                {"month": "2025-01", "yoy": 4.0, "forecast": 3.8},
                {"month": "2025-02", "yoy": 4.0, "forecast": 3.9},
                {"month": "2025-03", "yoy": 4.0, "forecast": 3.9},
                {"month": "2025-04", "yoy": 3.9, "forecast": 3.8},
                {"month": "2025-05", "yoy": 3.9, "forecast": 3.9},
                {"month": "2025-06", "yoy": 3.9, "forecast": 3.9},
                {"month": "2025-07", "yoy": 4.0, "forecast": 3.9},
                {"month": "2025-08", "yoy": 3.8, "forecast": 3.9}
            ]
        },
        # 先行指標・関連指標（ミニグラフ用データ含む）
        "leading_indicators": {
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
        # 州別データ（ヒートマップ用）
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
            "bonds": {"us10y": -5, "us2y": -3},  # bp単位
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

def create_enhanced_html_report():
    """改善されたHTMLレポートを作成"""
    
    data = get_enhanced_employment_data()
    
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
    .cols-4{{grid-template-columns:repeat(4,1fr)}}
    @media(max-width:800px){{.cols-2,.cols-3,.cols-4{{grid-template-columns:1fr}}}}

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
    
    .us-map-container{{
      margin:20px 0;
      text-align:center;
    }}
    
    .state-path{{
      fill:#e9ecef;
      stroke:#ffffff;
      stroke-width:1;
      cursor:pointer;
      transition:all 0.2s;
    }}
    
    .state-path:hover{{
      stroke:#000000;
      stroke-width:2;
      transform:scale(1.05);
      transform-origin:center;
    }}
    
    .state-path.low{{fill:#d4edda}}
    .state-path.medium{{fill:#fff3cd}}
    .state-path.high{{fill:#f8d7da}}
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
      <h2>平均時給（前年比）</h2>
      <div class="kpi">+{data["indicators"]["average_hourly_earnings_yoy"]["actual"]}% YoY</div>
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

  <!-- 先行指標・関連指標 -->
  <div class="card">
    <h2>先行指標・関連指標</h2>
    <div class="leading-indicators">
      <div class="indicator-card">
        <div class="indicator-value">{data["leading_indicators"]["jolts"]["job_openings"]["current"]}</div>
        <div class="indicator-label">JOLTS求人数（百万件）</div>
        <div class="mini-chart">
          <canvas id="joltsOpeningsChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">{data["leading_indicators"]["jolts"]["hires"]["current"]}</div>
        <div class="indicator-label">JOLTS採用数（百万件）</div>
        <div class="mini-chart">
          <canvas id="joltsHiresChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">{data["leading_indicators"]["jolts"]["quits"]["current"]}</div>
        <div class="indicator-label">JOLTS離職数（百万件）</div>
        <div class="mini-chart">
          <canvas id="joltsQuitsChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">{data["leading_indicators"]["adp"]["current"]}</div>
        <div class="indicator-label">ADP雇用（千人）</div>
        <div class="mini-chart">
          <canvas id="adpChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">{data["leading_indicators"]["ism_employment"]["current"]}</div>
        <div class="indicator-label">ISM雇用指数</div>
        <div class="mini-chart">
          <canvas id="ismChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">{data["leading_indicators"]["challenger_job_cuts"]["current"]}</div>
        <div class="indicator-label">Challenger解雇（千人）</div>
        <div class="mini-chart">
          <canvas id="challengerChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">{data["leading_indicators"]["weekly_claims"]["current"]}</div>
        <div class="indicator-label">週次失業保険申請（千人）</div>
        <div class="mini-chart">
          <canvas id="claimsChart"></canvas>
        </div>
      </div>
      <div class="indicator-card">
        <div class="indicator-value">{data["leading_indicators"]["nfib_labor_shortage"]["current"]}</div>
        <div class="indicator-label">NFIB労働力不足（%）</div>
        <div class="mini-chart">
          <canvas id="nfibChart"></canvas>
        </div>
      </div>
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
    <div class="us-map-container">
      <svg id="usMap" viewBox="0 0 1000 600" style="width: 100%; height: 400px;">
        <!-- 簡略化された米国地図のSVGパス -->
        <g id="states">
          <!-- カリフォルニア -->
          <path id="CA" d="M50 200 L150 180 L180 250 L120 280 L80 260 Z" 
                class="state-path" data-state="CA" data-unemployment="4.8" data-employment-change="-0.2"/>
          <!-- テキサス -->
          <path id="TX" d="M200 300 L350 280 L380 350 L320 380 L250 360 Z" 
                class="state-path" data-state="TX" data-unemployment="4.1" data-employment-change="0.3"/>
          <!-- フロリダ -->
          <path id="FL" d="M600 400 L700 380 L720 450 L650 480 L580 460 Z" 
                class="state-path" data-state="FL" data-unemployment="3.9" data-employment-change="0.1"/>
          <!-- ニューヨーク -->
          <path id="NY" d="M750 150 L850 130 L870 200 L800 230 L730 210 Z" 
                class="state-path" data-state="NY" data-unemployment="4.5" data-employment-change="-0.1"/>
          <!-- ペンシルベニア -->
          <path id="PA" d="M700 200 L800 180 L820 250 L750 280 L680 260 Z" 
                class="state-path" data-state="PA" data-unemployment="4.2" data-employment-change="0.0"/>
          <!-- イリノイ -->
          <path id="IL" d="M500 250 L600 230 L620 300 L550 330 L480 310 Z" 
                class="state-path" data-state="IL" data-unemployment="4.6" data-employment-change="-0.2"/>
          <!-- オハイオ -->
          <path id="OH" d="M600 200 L700 180 L720 250 L650 280 L580 260 Z" 
                class="state-path" data-state="OH" data-unemployment="4.0" data-employment-change="0.1"/>
          <!-- ジョージア -->
          <path id="GA" d="M550 350 L650 330 L670 400 L600 430 L530 410 Z" 
                class="state-path" data-state="GA" data-unemployment="3.8" data-employment-change="0.2"/>
          <!-- ノースカロライナ -->
          <path id="NC" d="M650 300 L750 280 L770 350 L700 380 L630 360 Z" 
                class="state-path" data-state="NC" data-unemployment="3.7" data-employment-change="0.2"/>
          <!-- ミシガン -->
          <path id="MI" d="M550 150 L650 130 L670 200 L600 230 L530 210 Z" 
                class="state-path" data-state="MI" data-unemployment="4.3" data-employment-change="0.0"/>
          <!-- その他の州（簡略化） -->
          <path id="WA" d="M50 100 L150 80 L180 150 L120 180 L80 160 Z" 
                class="state-path" data-state="WA" data-unemployment="4.7" data-employment-change="-0.1"/>
          <path id="AZ" d="M100 250 L200 230 L220 300 L150 330 L80 310 Z" 
                class="state-path" data-state="AZ" data-unemployment="4.2" data-employment-change="0.1"/>
          <path id="MA" d="M800 100 L900 80 L920 150 L850 180 L780 160 Z" 
                class="state-path" data-state="MA" data-unemployment="4.1" data-employment-change="0.0"/>
          <path id="TN" d="M500 300 L600 280 L620 350 L550 380 L480 360 Z" 
                class="state-path" data-state="TN" data-unemployment="3.6" data-employment-change="0.2"/>
          <path id="IN" d="M550 250 L650 230 L670 300 L600 330 L530 310 Z" 
                class="state-path" data-state="IN" data-unemployment="3.8" data-employment-change="0.1"/>
          <path id="MO" d="M450 300 L550 280 L570 350 L500 380 L430 360 Z" 
                class="state-path" data-state="MO" data-unemployment="3.9" data-employment-change="0.0"/>
          <path id="MD" d="M750 250 L850 230 L870 300 L800 330 L730 310 Z" 
                class="state-path" data-state="MD" data-unemployment="4.0" data-employment-change="0.0"/>
          <path id="WI" d="M500 200 L600 180 L620 250 L550 280 L480 260 Z" 
                class="state-path" data-state="WI" data-unemployment="3.7" data-employment-change="0.1"/>
        </g>
      </svg>
    </div>
    <div class="state-tooltip" id="stateTooltip"></div>
    <p class="note">簡略化された米国地図（実際のプロダクションではGeoJSONデータを使用）</p>
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
const leadingData = {json.dumps(data["leading_indicators"], ensure_ascii=False)};

createMiniChart('joltsOpeningsChart', leadingData.jolts.job_openings.trend, '#007bff');
createMiniChart('joltsHiresChart', leadingData.jolts.hires.trend, '#28a745');
createMiniChart('joltsQuitsChart', leadingData.jolts.quits.trend, '#ffc107');
createMiniChart('adpChart', leadingData.adp.trend, '#17a2b8');
createMiniChart('ismChart', leadingData.ism_employment.trend, '#6f42c1');
createMiniChart('challengerChart', leadingData.challenger_job_cuts.trend, '#dc3545');
createMiniChart('claimsChart', leadingData.weekly_claims.trend, '#fd7e14');
createMiniChart('nfibChart', leadingData.nfib_labor_shortage.trend, '#20c997');

// SVG地図の初期化
function initializeUSMap() {{
    const statePaths = document.querySelectorAll('.state-path');
    const tooltip = document.getElementById('stateTooltip');
    
    statePaths.forEach(path => {{
        const state = path.dataset.state;
        const unemployment = parseFloat(path.dataset.unemployment);
        
        // 失業率に基づいて色を設定
        if (unemployment <= 4.0) {{
            path.classList.add('low');
        }} else if (unemployment <= 4.5) {{
            path.classList.add('medium');
        }} else {{
            path.classList.add('high');
        }}
        
        // ホバーイベント
        path.addEventListener('mouseover', function(e) {{
            const employmentChange = path.dataset.employmentChange;
            tooltip.innerHTML = `
                <strong>${{state}}</strong><br/>
                失業率: ${{unemployment}}%<br/>
                雇用変化: ${{employmentChange}}%
            `;
            tooltip.style.display = 'block';
            tooltip.style.left = e.pageX + 10 + 'px';
            tooltip.style.top = e.pageY - 10 + 'px';
        }});
        
        path.addEventListener('mouseout', function() {{
            tooltip.style.display = 'none';
        }});
        
        path.addEventListener('mousemove', function(e) {{
            tooltip.style.left = e.pageX + 10 + 'px';
            tooltip.style.top = e.pageY - 10 + 'px';
        }});
    }});
}}

// 地図を初期化
initializeUSMap();
</script>
</body>
</html>
"""
    
    return html_content

def main():
    """メイン実行関数"""
    
    try:
        print("🚀 改善された雇用統計レポート生成を開始します...")
        
        # 出力ディレクトリを設定
        output_dir = Path("test_output/enhanced_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # HTMLレポートを生成
        html_content = create_enhanced_html_report()
        
        # ファイル名生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = output_dir / f"enhanced_employment_report_v3_{timestamp}.html"
        
        # HTMLファイルを保存
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print("✅ 改善された雇用統計レポート生成が完了しました！")
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
