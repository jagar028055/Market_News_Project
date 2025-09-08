#!/usr/bin/env python3
"""
Professional US Employment Map with Real GeoJSON Data
本格的なGeoJSONデータを使用した米国雇用統計地図
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
    # GitHubから実際のGeoJSONデータを取得
    url = "https://raw.githubusercontent.com/python-visualization/folium/main/examples/data/us-states.json"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"GeoJSONデータの取得に失敗しました: {e}")
        # フォールバック用の簡略化データ
        return get_fallback_geojson()

def get_fallback_geojson():
    """フォールバック用の簡略化GeoJSONデータ"""
    return {
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
            }
        ]
    }

def get_employment_data():
    """雇用統計データを取得"""
    return {
        "California": {"unemployment": 4.8, "employment_change": -0.2, "nfp_change": -15.2},
        "Texas": {"unemployment": 4.1, "employment_change": 0.3, "nfp_change": 8.5},
        "Florida": {"unemployment": 3.9, "employment_change": 0.1, "nfp_change": 5.2},
        "New York": {"unemployment": 4.5, "employment_change": -0.1, "nfp_change": -3.8},
        "Pennsylvania": {"unemployment": 4.2, "employment_change": 0.0, "nfp_change": 1.2},
        "Illinois": {"unemployment": 4.6, "employment_change": -0.2, "nfp_change": -8.9},
        "Ohio": {"unemployment": 4.0, "employment_change": 0.1, "nfp_change": 2.1},
        "Georgia": {"unemployment": 3.8, "employment_change": 0.2, "nfp_change": 6.8},
        "North Carolina": {"unemployment": 3.7, "employment_change": 0.2, "nfp_change": 7.3},
        "Michigan": {"unemployment": 4.3, "employment_change": 0.0, "nfp_change": -1.5},
        "New Jersey": {"unemployment": 4.4, "employment_change": -0.1, "nfp_change": -2.1},
        "Virginia": {"unemployment": 3.9, "employment_change": 0.1, "nfp_change": 3.4},
        "Washington": {"unemployment": 4.7, "employment_change": -0.1, "nfp_change": -4.2},
        "Arizona": {"unemployment": 4.2, "employment_change": 0.1, "nfp_change": 2.8},
        "Massachusetts": {"unemployment": 4.1, "employment_change": 0.0, "nfp_change": 0.8},
        "Tennessee": {"unemployment": 3.6, "employment_change": 0.2, "nfp_change": 4.1},
        "Indiana": {"unemployment": 3.8, "employment_change": 0.1, "nfp_change": 2.9},
        "Missouri": {"unemployment": 3.9, "employment_change": 0.0, "nfp_change": 1.7},
        "Maryland": {"unemployment": 4.0, "employment_change": 0.0, "nfp_change": 1.3},
        "Wisconsin": {"unemployment": 3.7, "employment_change": 0.1, "nfp_change": 2.4}
    }

def create_professional_employment_map():
    """本格的な雇用統計地図を作成"""
    
    # データを取得
    geojson_data = get_real_us_geojson()
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
        state_name = feature['properties']['name']
        
        if state_name in employment_data:
            data = employment_data[state_name]
            unemployment = data['unemployment']
            employment_change = data['employment_change']
            nfp_change = data['nfp_change']
            
            # ポップアップ用のHTML
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; width: 200px;">
                <h4 style="margin: 0 0 10px 0; color: #333;">{state_name}</h4>
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

def create_employment_report_with_professional_map():
    """本格的な地図を含む雇用統計レポートを作成"""
    
    # 地図を作成
    employment_map = create_professional_employment_map()
    
    # 出力ディレクトリを作成
    output_dir = Path("test_output/enhanced_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 地図をHTMLファイルとして保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    map_file = output_dir / f"professional_employment_map_{timestamp}.html"
    employment_map.save(str(map_file))
    
    print(f"✅ 本格的な雇用統計地図が生成されました: {map_file}")
    
    return map_file

def main():
    """メイン実行関数"""
    
    try:
        print("🗺️ 本格的なGeoJSONデータを使用した米国雇用統計地図生成を開始します...")
        
        # 地図を作成
        map_file = create_employment_report_with_professional_map()
        
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
