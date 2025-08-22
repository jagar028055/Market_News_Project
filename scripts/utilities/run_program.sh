#!/bin/bash

# プロジェクトディレクトリに移動
cd "/Users/satoissei/Desktop/VS Code/Cline/Market_News"

echo "=== Market News Program 実行開始 ==="
echo "現在のディレクトリ: $(pwd)"
echo "Python実行パス: $(which python3)"
echo "Python バージョン: $(python3 --version)"

# 仮想環境の作成と有効化
if [ ! -d "venv" ]; then
    echo "=== 仮想環境を作成します ==="
    python3 -m venv venv
fi
source venv/bin/activate

echo "=== 仮想環境有効化完了 ==="
echo "Python実行パス (venv): $(which python)"
echo "Python バージョン (venv): $(python --version)"

echo "=== 依存関係のインストール ==="
python -m pip install -r requirements.txt

# 環境変数の設定（テスト用）
export GOOGLE_DRIVE_OUTPUT_FOLDER_ID="dummy_folder_id"

echo "=== 環境変数設定完了 ==="
echo "GOOGLE_DRIVE_OUTPUT_FOLDER_ID: $GOOGLE_DRIVE_OUTPUT_FOLDER_ID"

echo "=== main.py実行開始 ==="
python main.py

echo "=== 実行完了 ==="
