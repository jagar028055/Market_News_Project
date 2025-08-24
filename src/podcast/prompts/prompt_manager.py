# -*- coding: utf-8 -*-

"""
プロンプト管理システム
動的なプロンプト読み込み・選択・A/Bテスト機能を提供
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

class PromptManager:
    """プロンプト管理クラス"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            prompts_dir: プロンプトディレクトリパス（オプション）
        """
        self.logger = logging.getLogger(__name__)
        
        # プロンプトディレクトリの設定
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            # デフォルト: このファイルと同じディレクトリ
            self.prompts_dir = Path(__file__).parent
            
        self.templates_dir = self.prompts_dir / "templates"
        self.configs_dir = self.prompts_dir / "configs"
        self.config_file = self.configs_dir / "prompt_configs.yaml"
        
        # 設定読み込み
        self.config = self._load_config()
        
        self.logger.info(f"プロンプト管理システム初期化完了: {self.prompts_dir}")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイル読み込み"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                self.logger.info("プロンプト設定ファイル読み込み完了")
                return config
            else:
                self.logger.warning("設定ファイルが見つかりません。デフォルト設定を使用")
                return self._get_default_config()
        except Exception as e:
            self.logger.error(f"設定ファイル読み込みエラー: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        return {
            "patterns": {
                "current_professional": {
                    "name": "現在のプロフェッショナル版",
                    "description": "現在使用中のプロンプト",
                    "template_file": "current_professional.txt",
                    "target_chars": 2700,
                    "temperature": 0.4,
                    "max_tokens": 4096,
                    "enabled": True
                }
            },
            "evaluation": {
                "target_char_range": [2650, 2750],
                "max_generation_time": 120,
                "min_structure_score": 0.7,
                "min_readability_score": 0.8
            }
        }
    
    def get_available_patterns(self) -> List[str]:
        """利用可能なプロンプトパターン一覧を取得"""
        patterns = []
        for pattern_id, pattern_config in self.config.get("patterns", {}).items():
            if pattern_config.get("enabled", True):
                patterns.append(pattern_id)
        return patterns
    
    def get_pattern_info(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """プロンプトパターンの詳細情報を取得"""
        return self.config.get("patterns", {}).get(pattern_id)
    
    def load_prompt_template(self, pattern_id: str, **kwargs) -> str:
        """
        プロンプトテンプレートを読み込み・変数置換
        
        Args:
            pattern_id: プロンプトパターンID
            **kwargs: テンプレート変数
            
        Returns:
            str: 生成されたプロンプト
        """
        try:
            pattern_config = self.get_pattern_info(pattern_id)
            if not pattern_config:
                raise ValueError(f"プロンプトパターンが見つかりません: {pattern_id}")
            
            template_file = pattern_config["template_file"]
            template_path = self.templates_dir / template_file
            
            if not template_path.exists():
                raise FileNotFoundError(f"テンプレートファイルが見つかりません: {template_path}")
            
            # テンプレート読み込み
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # 変数置換
            try:
                prompt = template.format(**kwargs)
            except KeyError as e:
                missing_var = str(e).strip("'\"")
                self.logger.warning(f"テンプレート変数が不足: {missing_var}")
                # 不足している変数をプレースホルダーで置換
                kwargs[missing_var] = f"[{missing_var}]"
                prompt = template.format(**kwargs)
            
            self.logger.info(f"プロンプト生成完了: {pattern_id} ({len(prompt)}文字)")
            return prompt
            
        except Exception as e:
            self.logger.error(f"プロンプト読み込みエラー ({pattern_id}): {e}")
            raise
    
    
    def get_generation_config(self, pattern_id: str) -> Dict[str, Any]:
        """プロンプトパターンのGemini生成設定を取得"""
        pattern_config = self.get_pattern_info(pattern_id)
        if not pattern_config:
            # デフォルト設定
            return {
                "temperature": 0.4,
                "max_output_tokens": 4096,
                "candidate_count": 1
            }
        
        return {
            "temperature": pattern_config.get("temperature", 0.4),
            "max_output_tokens": pattern_config.get("max_tokens", 4096),
            "candidate_count": 1
        }
    
    def setup_ab_test(self, patterns: Optional[List[str]] = None) -> List[str]:
        """
        A/Bテスト用のパターン設定
        
        Args:
            patterns: テストするパターンリスト（オプション）
            
        Returns:
            List[str]: テスト対象パターンリスト
        """
        if patterns:
            # 指定されたパターンを検証
            available_patterns = self.get_available_patterns()
            valid_patterns = [p for p in patterns if p in available_patterns]
            if not valid_patterns:
                self.logger.warning("有効なパターンがありません。デフォルトA/Bテストを使用")
                return self.config.get("ab_test", {}).get("default_patterns", ["current_professional"])
            return valid_patterns
        else:
            # デフォルトA/Bテスト設定を使用
            return self.config.get("ab_test", {}).get("default_patterns", ["current_professional"])
    
    def log_generation_result(self, pattern_id: str, result: Dict[str, Any]) -> None:
        """生成結果をログ記録"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "pattern_id": pattern_id,
                "pattern_name": (self.get_pattern_info(pattern_id) or {}).get("name", pattern_id),
                "result": result
            }
            
            # 結果ログファイルに追記
            log_file = self.prompts_dir / "generation_results.jsonl"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
            self.logger.info(f"生成結果ログ記録: {pattern_id}")
            
        except Exception as e:
            self.logger.error(f"生成結果ログ記録エラー: {e}")
    
    def get_pattern_comparison_report(self, patterns: List[str]) -> Dict[str, Any]:
        """パターン比較レポートを生成"""
        try:
            report = {
                "comparison_timestamp": datetime.now().isoformat(),
                "patterns": patterns,
                "pattern_details": {},
                "summary": {}
            }
            
            # 各パターンの詳細情報
            for pattern_id in patterns:
                pattern_info = self.get_pattern_info(pattern_id)
                if pattern_info:
                    report["pattern_details"][pattern_id] = {
                        "name": pattern_info.get("name", pattern_id),
                        "description": pattern_info.get("description", ""),
                        "config": {
                            "target_chars": pattern_info.get("target_chars", 2700),
                            "temperature": pattern_info.get("temperature", 0.4),
                            "max_tokens": pattern_info.get("max_tokens", 4096)
                        }
                    }
            
            # 比較サマリー
            report["summary"] = {
                "total_patterns": len(patterns),
                "enabled_patterns": len([p for p in patterns if (self.get_pattern_info(p) or {}).get("enabled", True)]),
                "comparison_metrics": self.config.get("ab_test", {}).get("comparison_metrics", [])
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"比較レポート生成エラー: {e}")
            return {"error": str(e)}
    
    def validate_environment(self) -> Dict[str, bool]:
        """環境検証（テンプレートファイル存在確認等）"""
        validation_results = {
            "config_file_exists": self.config_file.exists(),
            "templates_dir_exists": self.templates_dir.exists(),
            "available_patterns": []
        }
        
        # 各パターンのテンプレートファイル確認
        for pattern_id in self.get_available_patterns():
            pattern_config = self.get_pattern_info(pattern_id)
            if pattern_config:
                template_file = pattern_config["template_file"]
                template_path = self.templates_dir / template_file
                validation_results["available_patterns"].append({
                    "pattern_id": pattern_id,
                    "template_exists": template_path.exists(),
                    "template_path": str(template_path)
                })
        
        return validation_results
    
    def get_environment_prompt_pattern(self) -> str:
        """環境変数からプロンプトパターンを取得"""
        # 環境変数PODCAST_PROMPT_PATTERNを確認
        env_pattern = os.getenv("PODCAST_PROMPT_PATTERN")
        if env_pattern and env_pattern in self.get_available_patterns():
            self.logger.info(f"環境変数からプロンプトパターン選択: {env_pattern}")
            return env_pattern
        
        # デフォルト
        default_pattern = "current_professional"
        self.logger.info(f"デフォルトプロンプトパターン使用: {default_pattern}")
        return default_pattern