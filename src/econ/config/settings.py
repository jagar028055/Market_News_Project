"""
Economic Indicators Configuration Settings
経済指標設定

簡易的な設定クラス
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class EconConfig:
    """経済指標設定"""
    
    # 基本設定
    country: str = "US"
    analysis_date: str = "2024-01-01"
    
    # 出力設定
    output_base_dir: str = "./build"
    
    # データソース設定
    data_sources: Dict[str, Any] = field(default_factory=lambda: {
        'fred_api_key': None,
        'bls_api_key': None,
        'fmp_api_key': None,
        'finnhub_api_key': None
    })
    
    # API設定
    apis: Dict[str, Any] = field(default_factory=lambda: {
        'fred_api_key': None,
        'bls_api_key': None
    })
    
    # 対象国設定
    targets: Dict[str, Any] = field(default_factory=lambda: {
        'target_countries': ['US', 'EU', 'JP', 'UK', 'CA', 'AU']
    })
    
    # 出力設定
    output: Dict[str, Any] = field(default_factory=lambda: {
        'output_base_dir': './build',
        'report_formats': ['html', 'json'],
        'chart_formats': ['html', 'png'],
        'retention_days': 30,
        'timezone': 'UTC'
    })
    
    # レンダリング設定
    render: Dict[str, Any] = field(default_factory=lambda: {
        'japanese_fonts': True,
        'color_palette': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'],
        'figure_size': (12, 8),
        'recession_shading': True
    })
