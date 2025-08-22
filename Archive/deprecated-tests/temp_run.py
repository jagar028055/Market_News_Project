#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys

# 環境設定
os.environ['GOOGLE_DRIVE_OUTPUT_FOLDER_ID'] = 'dummy_folder_id'
os.environ['AI_GEMINI_API_KEY'] = 'dummy_api_key'

# プロジェクトディレクトリに移動
os.chdir('/Users/satoissei/Desktop/VS Code/Cline/Market_News')

print("=== プロジェクトディレクトリ確認 ===")
print(f"現在のディレクトリ: {os.getcwd()}")
print(f"main.pyファイルが存在するか: {os.path.exists('main.py')}")

print("\n=== Python環境確認 ===")
print(f"Python実行パス: {sys.executable}")
print(f"Pythonバージョン: {sys.version}")

print("\n=== main.pyの実行試行 ===")
try:
    result = subprocess.run([sys.executable, 'main.py'], 
                          capture_output=True, text=True, timeout=300)
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
except subprocess.TimeoutExpired:
    print("実行がタイムアウトしました（300秒）")
except Exception as e:
    print(f"実行エラー: {e}")