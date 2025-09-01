"""
クレジット自動挿入モジュール

RSSフィードやLINEメッセージにCC-BYクレジット情報を自動挿入
"""

import logging
from typing import Dict, List, Optional
from .asset_manager import AssetManager, AssetCredits


logger = logging.getLogger(__name__)


class CreditInserter:
    """クレジット自動挿入クラス"""

    def __init__(self, asset_manager: AssetManager):
        """
        Args:
            asset_manager: AssetManagerインスタンス
        """
        self.asset_manager = asset_manager

    def insert_rss_credits(self, rss_description: str) -> str:
        """
        RSSフィードの説明にクレジット情報を挿入

        Args:
            rss_description: 元のRSS説明文

        Returns:
            クレジット情報が追加された説明文
        """
        try:
            credits_text = self._format_credits_for_rss()
            if credits_text:
                return f"{rss_description}\\n\\n【使用音源クレジット】\\n{credits_text}"
            else:
                logger.warning("No credits information available for RSS")
                return rss_description

        except Exception as e:
            logger.error(f"Error inserting RSS credits: {e}")
            return rss_description

    def insert_line_credits(self, message: str) -> str:
        """
        LINEメッセージにクレジット情報を挿入

        Args:
            message: 元のLINEメッセージ

        Returns:
            クレジット情報が追加されたメッセージ
        """
        try:
            credits_text = self._format_credits_for_line()
            if credits_text:
                return f"{message}\\n\\n【音源クレジット】\\n{credits_text}"
            else:
                logger.warning("No credits information available for LINE")
                return message

        except Exception as e:
            logger.error(f"Error inserting LINE credits: {e}")
            return message

    def get_episode_credits(self) -> Dict[str, str]:
        """
        エピソード固有のクレジット情報を取得

        Returns:
            クレジット情報の辞書 (RSS用, LINE用, 短縮版)
        """
        try:
            return {
                "rss_credits": self._format_credits_for_rss(),
                "line_credits": self._format_credits_for_line(),
                "short_credits": self._format_credits_short(),
                "full_credits": self.asset_manager.get_credits_text(),
            }
        except Exception as e:
            logger.error(f"Error getting episode credits: {e}")
            return {"rss_credits": "", "line_credits": "", "short_credits": "", "full_credits": ""}

    def validate_license_compliance(self) -> Dict[str, bool]:
        """
        ライセンス準拠の検証

        Returns:
            検証結果の辞書
        """
        validation_results = {
            "assets_exist": True,
            "cc_by_compliance": True,
            "credits_complete": True,
        }

        try:
            # アセットファイルの存在確認
            asset_validation = self.asset_manager.validate_assets()
            validation_results["assets_exist"] = all(asset_validation.values())

            # CC-BYライセンス準拠確認
            credits = self.asset_manager.get_credits_info()
            if credits:
                cc_by_check = self._check_cc_by_licenses(credits)
                validation_results["cc_by_compliance"] = cc_by_check
            else:
                validation_results["cc_by_compliance"] = False

            # クレジット情報の完全性確認
            credits_text = self.asset_manager.get_credits_text()
            validation_results["credits_complete"] = bool(credits_text and len(credits_text) > 0)

            logger.info(f"License compliance validation: {validation_results}")

        except Exception as e:
            logger.error(f"Error validating license compliance: {e}")
            validation_results = {k: False for k in validation_results.keys()}

        return validation_results

    def _format_credits_for_rss(self) -> str:
        """RSS用のクレジット形式"""
        try:
            credits = self.asset_manager.get_credits_info()
            if not credits:
                return ""

            credit_lines = []
            assets = [
                ("イントロ", credits.intro_jingle),
                ("アウトロ", credits.outro_jingle),
                ("BGM", credits.background_music),
                ("効果音", credits.segment_transition),
            ]

            for asset_name, asset in assets:
                if asset:
                    line = f'• {asset_name}: "{asset.title}" by {asset.author} - {asset.license} ({asset.license_url})'
                    credit_lines.append(line)

            return "\\n".join(credit_lines)

        except Exception as e:
            logger.error(f"Error formatting RSS credits: {e}")
            return ""

    def _format_credits_for_line(self) -> str:
        """LINE用の短縮クレジット形式"""
        try:
            credits = self.asset_manager.get_credits_info()
            if not credits:
                return ""

            # LINEメッセージの文字数制限を考慮して短縮形式
            unique_authors = set()
            unique_licenses = set()

            assets = [
                credits.intro_jingle,
                credits.outro_jingle,
                credits.background_music,
                credits.segment_transition,
            ]

            for asset in assets:
                if asset:
                    unique_authors.add(asset.author)
                    unique_licenses.add(f"{asset.license} - {asset.license_url}")

            credits_parts = []
            if unique_authors:
                authors_text = ", ".join(sorted(unique_authors))
                credits_parts.append(f"音源提供: {authors_text}")

            if unique_licenses:
                # 最も一般的なライセンスを表示
                license_text = sorted(unique_licenses)[0]
                credits_parts.append(f"ライセンス: {license_text}")

            return "\\n".join(credits_parts)

        except Exception as e:
            logger.error(f"Error formatting LINE credits: {e}")
            return ""

    def _format_credits_short(self) -> str:
        """短縮版クレジット（Twitter等の文字数制限対応）"""
        try:
            credits = self.asset_manager.get_credits_info()
            if not credits:
                return ""

            # 最もシンプルな形式
            authors = set()
            assets = [
                credits.intro_jingle,
                credits.outro_jingle,
                credits.background_music,
                credits.segment_transition,
            ]

            for asset in assets:
                if asset:
                    authors.add(asset.author)

            if authors:
                authors_text = ", ".join(sorted(authors))
                return f"音源: {authors_text} (CC BY 4.0)"

            return ""

        except Exception as e:
            logger.error(f"Error formatting short credits: {e}")
            return ""

    def _check_cc_by_licenses(self, credits: AssetCredits) -> bool:
        """CC-BYライセンスの確認"""
        try:
            assets = [
                credits.intro_jingle,
                credits.outro_jingle,
                credits.background_music,
                credits.segment_transition,
            ]

            for asset in assets:
                if asset and not asset.license.startswith("CC BY"):
                    logger.warning(f"Non-CC-BY license found: {asset.license} for {asset.title}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking CC-BY licenses: {e}")
            return False
