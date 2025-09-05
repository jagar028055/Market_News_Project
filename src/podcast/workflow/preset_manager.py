"""
ポッドキャストワークフロー設定プリセット管理システム

複雑な7つの設定項目を3つの直感的な運用モードに簡素化します。
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from enum import Enum
import json
from pathlib import Path
import logging


class OperationMode(Enum):
    """運用モード定義"""
    PRODUCTION = "production"      # 🎙️ 本番運用 - 完全なポッドキャスト生成・配信
    DEVELOPMENT = "development"    # 🧪 開発テスト - テスト環境での動作確認
    SCRIPT_ONLY = "script_only"    # 📝 台本のみ - 台本生成のみ、音声・配信なし


@dataclass
class WorkflowSettings:
    """ワークフロー設定値を格納するデータクラス"""
    
    # 既存の7つの設定項目
    use_db_artifact: bool
    force_run: bool
    test_mode: bool
    weekdays_only: bool
    prompt_pattern: str
    comparison_mode: str
    script_only: bool
    
    # メタ情報
    operation_mode: str
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)
    
    def to_github_inputs(self) -> Dict[str, str]:
        """GitHub Actions入力形式に変換（全て文字列）"""
        return {
            "use_db_artifact": str(self.use_db_artifact).lower(),
            "force_run": str(self.force_run).lower(),
            "test_mode": str(self.test_mode).lower(),
            "weekdays_only": str(self.weekdays_only).lower(),
            "prompt_pattern": self.prompt_pattern,
            "comparison_mode": self.comparison_mode,
            "script_only": str(self.script_only).lower()
        }


class PresetManager:
    """プリセット管理クラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._presets = self._initialize_default_presets()
    
    def _initialize_default_presets(self) -> Dict[str, WorkflowSettings]:
        """デフォルトプリセットを初期化"""
        
        presets = {
            # 🎙️ 本番運用モード - 日常の完全なポッドキャスト生成・配信
            OperationMode.PRODUCTION.value: WorkflowSettings(
                use_db_artifact=True,           # メインワークフローのDBを使用
                force_run=False,                # 条件チェックを尊重
                test_mode=False,                # 実際に配信
                weekdays_only=False,            # 毎日配信可能
                prompt_pattern="current_professional",  # 高品質プロンプト
                comparison_mode="single",       # 単一パターンで安定配信
                script_only=False,              # 完全なポッドキャスト生成
                operation_mode=OperationMode.PRODUCTION.value,
                description="本番運用：完全なポッドキャスト生成・配信"
            ),
            
            # 🧪 開発テストモード - 開発・デバッグ時の動作確認
            OperationMode.DEVELOPMENT.value: WorkflowSettings(
                use_db_artifact=True,           # 実データでテスト
                force_run=True,                 # 条件を無視して強制実行
                test_mode=True,                 # テストモード（配信なし）
                weekdays_only=False,            # いつでもテスト可能
                prompt_pattern="current_professional",  # 安定したプロンプト
                comparison_mode="single",       # テストは単一パターン
                script_only=False,              # 音声生成もテスト
                operation_mode=OperationMode.DEVELOPMENT.value,
                description="開発テスト：テストモードでの動作確認"
            ),
            
            # 📝 台本のみモード - 台本生成のみ、音声・配信なし
            OperationMode.SCRIPT_ONLY.value: WorkflowSettings(
                use_db_artifact=True,           # 実データで台本生成
                force_run=False,                # 通常の条件チェック
                test_mode=True,                 # 配信処理はスキップ
                weekdays_only=False,            # いつでも台本生成可能
                prompt_pattern="current_professional",  # 高品質台本
                comparison_mode="single",       # 単一パターン
                script_only=True,               # 台本のみ生成
                operation_mode=OperationMode.SCRIPT_ONLY.value,
                description="台本のみ：台本生成のみ、音声・配信なし"
            )
        }
        
        return presets
    
    def get_available_modes(self) -> List[str]:
        """利用可能な運用モード一覧を取得"""
        return list(self._presets.keys())
    
    def get_mode_info(self, mode: str) -> Optional[Dict[str, str]]:
        """運用モードの情報を取得"""
        if mode not in self._presets:
            return None
            
        preset = self._presets[mode]
        return {
            "mode": mode,
            "description": preset.description,
            "icon": self._get_mode_icon(mode)
        }
    
    def _get_mode_icon(self, mode: str) -> str:
        """運用モードのアイコンを取得"""
        icons = {
            OperationMode.PRODUCTION.value: "🎙️",
            OperationMode.DEVELOPMENT.value: "🧪", 
            OperationMode.SCRIPT_ONLY.value: "📝"
        }
        return icons.get(mode, "⚙️")
    
    def get_settings(self, mode: str) -> Optional[WorkflowSettings]:
        """指定した運用モードの設定を取得"""
        return self._presets.get(mode)
    
    def get_github_inputs(self, mode: str) -> Optional[Dict[str, str]]:
        """GitHub Actions入力形式で設定を取得"""
        settings = self.get_settings(mode)
        if not settings:
            return None
        return settings.to_github_inputs()
    
    def create_custom_preset(self, 
                           name: str, 
                           description: str,
                           **custom_settings) -> bool:
        """カスタムプリセットを作成"""
        try:
            # ベースとなる設定（本番運用をベース）
            base_settings = self._presets[OperationMode.PRODUCTION.value]
            
            # カスタム設定で上書き
            settings_dict = asdict(base_settings)
            settings_dict.update(custom_settings)
            settings_dict["operation_mode"] = name
            settings_dict["description"] = description
            
            # 新しいプリセットを作成
            custom_preset = WorkflowSettings(**settings_dict)
            self._presets[name] = custom_preset
            
            self.logger.info(f"カスタムプリセット作成完了: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"カスタムプリセット作成エラー: {e}")
            return False
    
    def validate_settings(self, settings: WorkflowSettings) -> List[str]:
        """設定値の妥当性をチェック"""
        issues = []
        
        # prompt_patternの妥当性チェック
        valid_patterns = [
            "current_professional", "cot_enhanced", "enhanced_persona",
            "few_shot_learning", "constraint_optimization", "context_aware", "minimalist"
        ]
        if settings.prompt_pattern not in valid_patterns:
            issues.append(f"無効なプロンプトパターン: {settings.prompt_pattern}")
        
        # comparison_modeの妥当性チェック
        valid_modes = ["single", "ab_test", "multi_compare"]
        if settings.comparison_mode not in valid_modes:
            issues.append(f"無効な比較モード: {settings.comparison_mode}")
        
        # 論理的な組み合わせチェック
        if settings.script_only and not settings.test_mode:
            issues.append("台本のみモードの場合はtest_modeも有効にすべきです")
        
        if settings.force_run and not settings.test_mode:
            issues.append("本番環境でのforce_runは推奨されません")
        
        return issues
    
    def export_presets(self, file_path: Optional[Path] = None) -> str:
        """プリセットをJSONファイルにエクスポート"""
        try:
            presets_data = {}
            for name, preset in self._presets.items():
                presets_data[name] = preset.to_dict()
            
            json_data = json.dumps(presets_data, indent=2, ensure_ascii=False)
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_data)
                self.logger.info(f"プリセットをエクスポート: {file_path}")
            
            return json_data
            
        except Exception as e:
            self.logger.error(f"プリセットエクスポートエラー: {e}")
            return ""
    
    def import_presets(self, file_path: Path) -> bool:
        """JSONファイルからプリセットをインポート"""
        try:
            if not file_path.exists():
                self.logger.error(f"プリセットファイルが見つかりません: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                presets_data = json.load(f)
            
            imported_count = 0
            for name, preset_dict in presets_data.items():
                try:
                    preset = WorkflowSettings(**preset_dict)
                    self._presets[name] = preset
                    imported_count += 1
                except Exception as e:
                    self.logger.warning(f"プリセット '{name}' のインポート失敗: {e}")
            
            self.logger.info(f"プリセットをインポート: {imported_count}個")
            return imported_count > 0
            
        except Exception as e:
            self.logger.error(f"プリセットインポートエラー: {e}")
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """プリセットマネージャーの概要を取得"""
        summary = {
            "total_presets": len(self._presets),
            "available_modes": list(self._presets.keys()),
            "mode_details": {}
        }
        
        for mode, preset in self._presets.items():
            summary["mode_details"][mode] = {
                "description": preset.description,
                "icon": self._get_mode_icon(mode),
                "script_only": preset.script_only,
                "test_mode": preset.test_mode
            }
        
        return summary


def create_preset_manager() -> PresetManager:
    """プリセットマネージャーのファクトリー関数"""
    return PresetManager()


if __name__ == "__main__":
    # テスト用の簡単な動作確認
    manager = create_preset_manager()
    
    print("🚀 プリセットマネージャーテスト")
    print(f"利用可能モード: {manager.get_available_modes()}")
    
    for mode in manager.get_available_modes():
        info = manager.get_mode_info(mode)
        settings = manager.get_settings(mode)
        print(f"\n{info['icon']} {mode}:")
        print(f"  説明: {info['description']}")
        print(f"  設定: script_only={settings.script_only}, test_mode={settings.test_mode}")
    
    # プリセット概要表示
    summary = manager.get_summary()
    print(f"\n📊 概要: {summary['total_presets']}個のプリセット定義済み")