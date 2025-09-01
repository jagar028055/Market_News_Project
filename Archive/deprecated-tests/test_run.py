#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess

# Change to the project directory
project_dir = "/Users/satoissei/Desktop/VS Code/Cline/Market_News"
os.chdir(project_dir)

print("=== プロジェクトディレクトリ確認 ===")
print(f"現在のディレクトリ: {os.getcwd()}")
print(f"main.pyファイルが存在するか: {os.path.exists('main.py')}")

print("\n=== Python環境確認 ===")
print(f"Python実行パス: {sys.executable}")
print(f"Pythonバージョン: {sys.version}")

print("\n=== 必要なパッケージの確認 ===")
required_packages = [
    'selenium', 'beautifulsoup4', 'requests', 'pytz', 'python-dateutil',
    'google-generativeai', 'python-dotenv'
]

for package in required_packages:
    try:
        __import__(package.replace('-', '_'))
        print(f"✓ {package}: インストール済み")
    except ImportError:
        print(f"✗ {package}: インストールされていません")

print("\n=== 環境変数の確認 ===")
print(f"GOOGLE_DRIVE_OUTPUT_FOLDER_ID: {os.getenv('GOOGLE_DRIVE_OUTPUT_FOLDER_ID', '未設定')}")
print(f"AI_GEMINI_API_KEY: {'設定済み' if os.getenv('AI_GEMINI_API_KEY') else '未設定'}")

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