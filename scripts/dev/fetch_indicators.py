#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path
from datetime import datetime
import json

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.config.app_config import get_config
from src.indicators.fetcher import fetch_indicators


def main():
    cfg = get_config()
    date_key = datetime.now().strftime('%Y%m%d')
    out_dir = Path(cfg.social.output_base_dir) / 'indicators'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{date_key}.json'

    data = fetch_indicators()
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'書き出し: {out_path}')


if __name__ == '__main__':
    main()

