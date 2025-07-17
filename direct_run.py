#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess

# 環境設定
os.environ['GOOGLE_DRIVE_OUTPUT_FOLDER_ID'] = 'dummy_folder_id'
os.environ['AI_GEMINI_API_KEY'] = 'dummy_api_key'

# プロジェクトディレクトリに移動
os.chdir('/Users/satoissei/Desktop/VS Code/Cline/Market_News')

# main.pyを直接実行
print("=== main.pyを直接実行します ===")
try:
    # main.pyを直接インポートして実行
    exec(open('main.py').read())
except Exception as e:
    print(f"実行エラー: {e}")
    import traceback
    traceback.print_exc()