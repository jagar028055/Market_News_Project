# -*- coding: utf-8 -*-

"""
ポッドキャスト台本の品質分析機能
"""

import logging
import re
from typing import Dict, Any, Tuple, List

class ScriptAnalyzer:
    """
    ポッドキャスト台本を分析し、品質メトリクスを評価するクラス。
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def analyze(self, script: str) -> Dict[str, Any]:
        """
        台本コンテンツの詳細な分析を実行します。

        Args:
            script: 分析対象の台本テキスト。

        Returns:
            分析結果を含む辞書。
        """
        lines = script.split('\n')
        char_count = len(script)

        speaker_a_lines, speaker_b_lines, other_lines = 0, 0, 0
        speaker_a_chars, speaker_b_chars = 0, 0
        long_lines, empty_lines = 0, 0

        for line in lines:
            line = line.strip()
            if not line:
                empty_lines += 1
                continue
            if line.startswith('A:'):
                speaker_a_lines += 1
                speaker_a_chars += len(line[2:].strip())
            elif line.startswith('B:'):
                speaker_b_lines += 1
                speaker_b_chars += len(line[2:].strip())
            elif line:
                other_lines += 1
            if len(line) > 120:  # 120文字を超える行はTTSで読みにくい可能性がある
                long_lines += 1

        estimated_minutes = char_count / 400.0  # 日本語の平均的な朗読速度

        issues, warnings = self._detect_problems(
            char_count, speaker_a_lines, speaker_b_lines,
            speaker_a_chars, speaker_b_chars, long_lines, other_lines, script
        )

        structure_score = self._calculate_structure_score(char_count, long_lines, issues, warnings)
        proper_start, proper_end = self._check_structure_patterns(script)

        return {
            'char_count': char_count, 'line_count': len(lines), 'empty_lines': empty_lines,
            'speaker_a_lines': speaker_a_lines, 'speaker_b_lines': speaker_b_lines,
            'speaker_a_chars': speaker_a_chars, 'speaker_b_chars': speaker_b_chars,
            'other_lines': other_lines, 'long_lines': long_lines,
            'estimated_minutes': estimated_minutes, 'issues': issues, 'warnings': warnings,
            'structure_score': structure_score, 'proper_start': proper_start, 'proper_end': proper_end,
            'speaker_balance_ratio': speaker_a_chars / speaker_b_chars if speaker_b_chars > 0 else 0,
        }

    def _detect_problems(self, char_count: int, a_lines: int, b_lines: int, a_chars: int, b_chars: int, long_lines: int, other_lines: int, script: str) -> Tuple[List[str], List[str]]:
        """台本内の潜在的な問題を検出します。"""
        issues = []
        warnings = []
        if char_count < 1000: issues.append("台本が短すぎます（1000文字未満）")
        if char_count > 8000: issues.append("台本が長すぎます（8000文字超過）")
        if a_lines == 0 and b_lines > 0: issues.append("スピーカーAの台詞がありません")
        if b_lines == 0 and a_lines > 0: issues.append("スピーカーBの台詞がありません")

        total_speaker_lines = a_lines + b_lines
        if total_speaker_lines > 0 and abs(a_lines - b_lines) > max(a_lines, b_lines) * 0.4:
            warnings.append("スピーカー間の台詞数バランスが不均衡です。")
        if long_lines > 5: warnings.append(f"長すぎる行が{long_lines}行あります（TTS読み上げに不適切）")
        if other_lines > total_speaker_lines * 0.3: warnings.append("話者以外の行（ナレーション等）が多すぎます。")
        if a_chars > 0 and b_chars > 0 and (max(a_chars, b_chars) / min(a_chars, b_chars)) > 2.5:
            warnings.append("スピーカー間の発話量に大きな偏りがあります。")

        proper_start, proper_end = self._check_structure_patterns(script)
        if not proper_start: warnings.append("適切な開始挨拶が見つかりません。")
        if not proper_end: warnings.append("適切な終了挨拶が見つかりません。")

        return issues, warnings

    def _check_structure_patterns(self, script: str) -> Tuple[bool, bool]:
        """台本の開始・終了が適切かパターンマッチで確認します。"""
        start_patterns = [r'(みなさん|皆さん|皆様).*?(おはよう|こんにちは)', r'\d{4}年\d+月\d+日', r'(ポッドキャスト|番組).*?(時間|開始)']
        end_patterns = [r'明日.*?よろしく.*?お願い.*?します', r'以上.*?ポッドキャスト.*?でした', r'また.*?(明日|次回).*?お会い']
        proper_start = any(re.search(p, script[:200], re.IGNORECASE) for p in start_patterns)
        proper_end = any(re.search(p, script[-300:], re.IGNORECASE) for p in end_patterns)
        return proper_start, proper_end

    def _calculate_structure_score(self, char_count: int, long_lines: int, issues: List[str], warnings: List[str]) -> int:
        """台本の構造スコアを計算します。"""
        score = 100
        if not char_count: return 0
        if char_count < 2000: score -= 20
        elif char_count > 6000: score -= 10
        score -= min(20, long_lines * 2)
        score -= len(issues) * 15
        score -= len(warnings) * 5
        return max(0, score)

    def display_analysis(self, analysis: Dict[str, Any], script_preview: str = "") -> None:
        """分析結果を人間が読みやすい形式でログに出力します。"""
        self.logger.info("=" * 60)
        self.logger.info("📄 台本分析結果（詳細版）")
        self.logger.info("=" * 60)

        est_min = int(analysis['estimated_minutes'])
        est_sec = int((analysis['estimated_minutes'] % 1) * 60)

        self.logger.info(f"📊 基本統計:")
        self.logger.info(f"  文字数: {analysis['char_count']:,}文字")
        self.logger.info(f"  総行数: {analysis['line_count']}行 (空行: {analysis['empty_lines']}行)")
        self.logger.info(f"  推定時間: {est_min}分{est_sec}秒")

        self.logger.info(f"\n🎭 スピーカー分析:")
        self.logger.info(f"  スピーカーA: {analysis['speaker_a_lines']}行 ({analysis['speaker_a_chars']:,}文字)")
        self.logger.info(f"  スピーカーB: {analysis['speaker_b_lines']}行 ({analysis['speaker_b_chars']:,}文字)")
        self.logger.info(f"  その他: {analysis['other_lines']}行")

        score_emoji = "🟢" if analysis['structure_score'] >= 80 else "🟡" if analysis['structure_score'] >= 60 else "🔴"
        self.logger.info(f"\n{score_emoji} 品質スコア: {analysis['structure_score']}/100")

        self.logger.info(f"  適切な開始: {'✅' if analysis['proper_start'] else '❌'}")
        self.logger.info(f"  適切な終了: {'✅' if analysis['proper_end'] else '❌'}")

        if analysis['issues']:
            self.logger.error(f"\n🚨 重大な問題 ({len(analysis['issues'])}件):")
            for i, issue in enumerate(analysis['issues'], 1):
                self.logger.error(f"  {i}. {issue}")

        if analysis['warnings']:
            self.logger.warning(f"\n⚠️ 警告 ({len(analysis['warnings'])}件):")
            for i, warning in enumerate(analysis['warnings'], 1):
                self.logger.warning(f"  {i}. {warning}")

        if not analysis['issues'] and not analysis['warnings']:
            self.logger.info(f"\n✅ 問題は検出されませんでした。")

        if script_preview:
            self.logger.info(f"\n📖 台本プレビュー（先頭500文字）:")
            self.logger.info("-" * 40)
            self.logger.info(script_preview[:500] + "...")
            self.logger.info("-" * 40)

        self.logger.info("=" * 60)
