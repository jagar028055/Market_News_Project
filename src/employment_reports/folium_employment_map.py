#!/usr/bin/env python3
"""
Folium-based US Employment Map Generator
GeoJSONとfoliumを使用した米国雇用統計地図生成
"""

import folium
import json
import pandas as pd
from pathlib import Path
import requests
import sys
import os
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def get_us_states_geojson():
    """米国の州のGeoJSONデータを取得"""
    # 簡略化されたGeoJSONデータ（実際のプロダクションでは外部APIから取得）
    us_states_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "California", "abbr": "CA"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-124.482, 32.529], [-114.131, 32.529], [-114.131, 35.001],
                        [-120.001, 35.001], [-120.001, 39.001], [-124.482, 39.001],
                        [-124.482, 32.529]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Texas", "abbr": "TX"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-106.646, 25.837], [-93.508, 25.837], [-93.508, 36.501],
                        [-106.646, 36.501], [-106.646, 25.837]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Florida", "abbr": "FL"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-87.635, 24.396], [-80.031, 24.396], [-80.031, 31.001],
                        [-87.635, 31.001], [-87.635, 24.396]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "New York", "abbr": "NY"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-79.762, 40.496], [-71.856, 40.496], [-71.856, 45.001],
                        [-79.762, 45.001], [-79.762, 40.496]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Pennsylvania", "abbr": "PA"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-80.520, 39.719], [-74.690, 39.719], [-74.690, 42.001],
                        [-80.520, 42.001], [-80.520, 39.719]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Illinois", "abbr": "IL"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-91.513, 36.970], [-87.019, 36.970], [-87.019, 42.508],
                        [-91.513, 42.508], [-91.513, 36.970]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Ohio", "abbr": "OH"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-84.820, 38.403], [-80.519, 38.403], [-80.519, 41.978],
                        [-84.820, 41.978], [-84.820, 38.403]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Georgia", "abbr": "GA"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-85.605, 30.356], [-80.840, 30.356], [-80.840, 35.001],
                        [-85.605, 35.001], [-85.605, 30.356]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "North Carolina", "abbr": "NC"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-84.322, 33.842], [-75.460, 33.842], [-75.460, 36.588],
                        [-84.322, 36.588], [-84.322, 33.842]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Michigan", "abbr": "MI"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-90.418, 41.696], [-82.122, 41.696], [-82.122, 48.238],
                        [-90.418, 48.238], [-90.418, 41.696]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "New Jersey", "abbr": "NJ"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-75.559, 38.928], [-73.894, 38.928], [-73.894, 41.357],
                        [-75.559, 41.357], [-75.559, 38.928]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Virginia", "abbr": "VA"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-83.675, 36.541], [-75.242, 36.541], [-75.242, 39.466],
                        [-83.675, 39.466], [-83.675, 36.541]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Washington", "abbr": "WA"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-124.763, 45.543], [-116.916, 45.543], [-116.916, 49.001],
                        [-124.763, 49.001], [-124.763, 45.543]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Arizona", "abbr": "AZ"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-114.816, 31.332], [-109.045, 31.332], [-109.045, 37.001],
                        [-114.816, 37.001], [-114.816, 31.332]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Massachusetts", "abbr": "MA"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-73.508, 41.187], [-69.858, 41.187], [-69.858, 42.887],
                        [-73.508, 42.887], [-73.508, 41.187]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Tennessee", "abbr": "TN"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-90.310, 34.983], [-81.647, 34.983], [-81.647, 36.678],
                        [-90.310, 36.678], [-90.310, 34.983]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Indiana", "abbr": "IN"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-88.098, 37.771], [-84.784, 37.771], [-84.784, 41.761],
                        [-88.098, 41.761], [-88.098, 37.771]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Missouri", "abbr": "MO"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-95.774, 35.995], [-89.099, 35.995], [-89.099, 40.614],
                        [-95.774, 40.614], [-95.774, 35.995]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Maryland", "abbr": "MD"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-79.488, 37.886], [-75.048, 37.886], [-75.048, 39.723],
                        [-79.488, 39.723], [-79.488, 37.886]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Wisconsin", "abbr": "WI"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-92.889, 42.491], [-86.250, 42.491], [-86.250, 47.308],
                        [-92.889, 47.308], [-92.889, 42.491]
                    ]]
                }
            }
        ]
    }
    return us_states_geojson

def get_employment_data():
    """雇用統計データを取得"""
    return {
        "CA": {"unemployment": 4.8, "employment_change": -0.2, "nfp_change": -15.2},
        "TX": {"unemployment": 4.1, "employment_change": 0.3, "nfp_change": 8.5},
        "FL": {"unemployment": 3.9, "employment_change": 0.1, "nfp_change": 5.2},
        "NY": {"unemployment": 4.5, "employment_change": -0.1, "nfp_change": -3.8},
        "PA": {"unemployment": 4.2, "employment_change": 0.0, "nfp_change": 1.2},
        "IL": {"unemployment": 4.6, "employment_change": -0.2, "nfp_change": -8.9},
        "OH": {"unemployment": 4.0, "employment_change": 0.1, "nfp_change": 2.1},
        "GA": {"unemployment": 3.8, "employment_change": 0.2, "nfp_change": 6.8},
        "NC": {"unemployment": 3.7, "employment_change": 0.2, "nfp_change": 7.3},
        "MI": {"unemployment": 4.3, "employment_change": 0.0, "nfp_change": -1.5},
        "NJ": {"unemployment": 4.4, "employment_change": -0.1, "nfp_change": -2.1},
        "VA": {"unemployment": 3.9, "employment_change": 0.1, "nfp_change": 3.4},
        "WA": {"unemployment": 4.7, "employment_change": -0.1, "nfp_change": -4.2},
        "AZ": {"unemployment": 4.2, "employment_change": 0.1, "nfp_change": 2.8},
        "MA": {"unemployment": 4.1, "employment_change": 0.0, "nfp_change": 0.8},
        "TN": {"unemployment": 3.6, "employment_change": 0.2, "nfp_change": 4.1},
        "IN": {"unemployment": 3.8, "employment_change": 0.1, "nfp_change": 2.9},
        "MO": {"unemployment": 3.9, "employment_change": 0.0, "nfp_change": 1.7},
        "MD": {"unemployment": 4.0, "employment_change": 0.0, "nfp_change": 1.3},
        "WI": {"unemployment": 3.7, "employment_change": 0.1, "nfp_change": 2.4}
    }

def create_employment_map():
    """雇用統計地図を作成"""
    
    # データを取得
    geojson_data = get_us_states_geojson()
    employment_data = get_employment_data()
    
    # 地図の中心点（米国の中心）
    center_lat, center_lon = 39.8283, -98.5795
    
    # Folium地図を作成
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles='OpenStreetMap'
    )
    
    # 失業率に基づく色分け関数
    def get_color(unemployment_rate):
        if unemployment_rate <= 3.8:
            return '#2E8B57'  # 緑（低失業率）
        elif unemployment_rate <= 4.2:
            return '#FFD700'  # 黄（中程度失業率）
        elif unemployment_rate <= 4.5:
            return '#FF8C00'  # オレンジ（やや高失業率）
        else:
            return '#DC143C'  # 赤（高失業率）
    
    # 各州にデータを追加
    for feature in geojson_data['features']:
        state_abbr = feature['properties']['abbr']
        state_name = feature['properties']['name']
        
        if state_abbr in employment_data:
            data = employment_data[state_abbr]
            unemployment = data['unemployment']
            employment_change = data['employment_change']
            nfp_change = data['nfp_change']
            
            # ポップアップ用のHTML
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; width: 200px;">
                <h4 style="margin: 0 0 10px 0; color: #333;">{state_name} ({state_abbr})</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd;"><strong>失業率:</strong></td>
                        <td style="padding: 5px; border-bottom: 1px solid #ddd; text-align: right;">{unemployment}%</td>
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
                style_function=lambda x, unemployment=unemployment: {
                    'fillColor': get_color(unemployment),
                    'color': 'white',
                    'weight': 2,
                    'fillOpacity': 0.7
                },
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{state_name}: 失業率 {unemployment}%"
            ).add_to(m)
    
    # 凡例を追加
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 150px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <p><b>失業率</b></p>
    <p><i class="fa fa-square" style="color:#2E8B57"></i> ≤3.8% (低)</p>
    <p><i class="fa fa-square" style="color:#FFD700"></i> 3.8-4.2% (中)</p>
    <p><i class="fa fa-square" style="color:#FF8C00"></i> 4.2-4.5% (やや高)</p>
    <p><i class="fa fa-square" style="color:#DC143C"></i> >4.5% (高)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def create_employment_report_with_map():
    """地図を含む雇用統計レポートを作成"""
    
    # 地図を作成
    employment_map = create_employment_map()
    
    # 出力ディレクトリを作成
    output_dir = Path("test_output/enhanced_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 地図をHTMLファイルとして保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    map_file = output_dir / f"employment_map_{timestamp}.html"
    employment_map.save(str(map_file))
    
    print(f"✅ 雇用統計地図が生成されました: {map_file}")
    
    # 地図のHTMLを取得して、メインレポートに埋め込むための準備
    with open(map_file, 'r', encoding='utf-8') as f:
        map_html = f.read()
    
    return map_file, map_html

def main():
    """メイン実行関数"""
    
    try:
        print("🗺️ Foliumを使用した米国雇用統計地図生成を開始します...")
        
        # 地図を作成
        map_file, map_html = create_employment_report_with_map()
        
        print(f"📁 生成されたファイル: {map_file}")
        print(f"🌐 地図URL: file://{os.path.abspath(map_file)}")
        
        # ブラウザで開く
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(map_file)}")
        print("🔍 ブラウザで地図を開きました")
        
        return str(map_file)
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = main()
