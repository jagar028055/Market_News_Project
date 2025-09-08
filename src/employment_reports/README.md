# 雇用統計レポート生成システム

## 📁 ディレクトリ構造

```
src/employment_reports/
├── README.md                           # このファイル
├── integrated_employment_report.py     # メインの統合レポート生成（推奨）
├── folium_employment_map.py           # Folium地図生成
├── professional_employment_map.py     # 本格的な地図生成
└── legacy/                            # 過去バージョン（参考用）
    ├── complete_employment_report.py
    ├── employment_report_monotone.py
    ├── enhanced_employment_report_v3.py
    └── latest_employment_report.py
```

## 🚀 使用方法

### メインの統合レポート生成（推奨）
```bash
cd src/employment_reports/
python3 integrated_employment_report.py
```

### 地図のみ生成
```bash
cd src/employment_reports/
python3 folium_employment_map.py
# または
python3 professional_employment_map.py
```

## ✨ 機能

### integrated_employment_report.py（メイン）
- **Zスコア分析**: 過去12ヶ月のトレンドからの変化を統計的に分析
- **Folium地図**: 本格的なGeoJSONデータを使用した米国地図
- **全50州データ**: 失業率、雇用変化、NFP変化の包括的分析
- **インタラクティブ機能**: ホバー効果、ポップアップ、ズーム
- **Chart.js統合**: 美しいグラフとチャート
- **先行指標**: ミニグラフ付きでトレンド表示
- **2軸表示**: U3/U6失業率の詳細分析
- **最新データ**: 2025年8月分の雇用統計

### 地図生成スクリプト
- **folium_employment_map.py**: 基本的なFolium地図生成
- **professional_employment_map.py**: 本格的なGeoJSONデータを使用

### legacy/（過去バージョン）
- 開発過程での過去バージョン（参考用）
- 機能は統合版に統合済み

## 📊 出力

生成されたHTMLレポートは `test_output/enhanced_reports/` に保存されます。

## 🔧 必要なライブラリ

```bash
pip install folium pandas requests
```

## 📈 分析手法

- **Zスコア分析**: 各州の過去パフォーマンスと比較した相対的分析
- **統計的正確性**: 標準化された分析手法
- **トレンド重視**: 絶対値ではなく変化の方向性を重視
- **5段階色分け**: 大幅改善〜大幅悪化まで詳細な分析

## 🎨 デザイン

- **モノトーンクラシック**: 読みやすく印刷にも適している
- **レスポンシブデザイン**: デスクトップ・モバイル対応
- **プロフェッショナル**: 金融機関レベルの品質
