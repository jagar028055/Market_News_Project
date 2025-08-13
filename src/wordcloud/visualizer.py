# -*- coding: utf-8 -*-
"""
ワードクラウド視覚化コンポーネント

WordCloudライブラリを使用してワードクラウド画像を生成します。
"""

import io
import base64
from typing import Dict, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from wordcloud import WordCloud

from .config import WordCloudConfig


@dataclass
class ImageResult:
    """画像生成結果"""
    success: bool
    image_base64: Optional[str] = None
    image_size_bytes: Optional[int] = None
    quality_score: float = 0.0
    error_message: Optional[str] = None


class WordCloudVisualizer:
    """ワードクラウド視覚化コンポーネント
    
    単語頻度データから美しいワードクラウド画像を生成します。
    """
    
    def __init__(self, config: WordCloudConfig):
        """初期化
        
        Args:
            config: ワードクラウド設定
        """
        self.config = config
    
    def create_wordcloud_image(self, word_frequencies: Dict[str, int]) -> ImageResult:
        """ワードクラウド画像を生成
        
        Args:
            word_frequencies: 単語頻度辞書
            
        Returns:
            画像生成結果
        """
        try:
            if not word_frequencies:
                return ImageResult(
                    success=False,
                    error_message="単語頻度データが空です"
                )
            
            # 1. WordCloudオブジェクトを作成（シンプル設定）
            wordcloud_kwargs = {
                'width': self.config.width,
                'height': self.config.height,
                'background_color': self.config.background_color,
                'max_words': self.config.max_words,
                'min_font_size': self.config.font_size_min,
                'max_font_size': self.config.font_size_max,
                'colormap': self.config.colormap,
                'prefer_horizontal': self.config.prefer_horizontal,
                'relative_scaling': 0.5,
                'random_state': 42  # 再現性確保
            }
            
            # フォントパスが有効な場合のみ追加
            if self.config.font_path and self.config.font_path.strip():
                wordcloud_kwargs['font_path'] = self.config.font_path
            
            wordcloud = WordCloud(**wordcloud_kwargs)
            
            # 2. シンプルなデフォルト設定を使用（カスタム色関数は一時的に無効化）
            # wordcloud.color_func = self._create_color_function()
            
            # 3. 頻度データの型を確実に整数に変換
            safe_frequencies = {}
            for word, freq in word_frequencies.items():
                try:
                    # 文字列を整数に変換
                    safe_freq = int(freq) if freq > 0 else 1
                    safe_frequencies[str(word)] = safe_freq
                except (ValueError, TypeError):
                    # 変換できない場合はデフォルト値
                    safe_frequencies[str(word)] = 1
            
            # 4. ワードクラウドを生成
            wordcloud.generate_from_frequencies(safe_frequencies)
            
            # 4. 画像をbase64エンコード
            image_base64 = self._wordcloud_to_base64(wordcloud)
            
            # 5. 画像サイズを計算
            image_size_bytes = len(base64.b64decode(image_base64))
            
            # 6. 品質スコアを計算
            quality_score = self._calculate_image_quality(
                wordcloud, word_frequencies, image_size_bytes
            )
            
            return ImageResult(
                success=True,
                image_base64=image_base64,
                image_size_bytes=image_size_bytes,
                quality_score=quality_score
            )
            
        except Exception as e:
            return ImageResult(
                success=False,
                error_message=f"画像生成エラー: {str(e)}"
            )
    
    def _create_color_function(self):
        """カスタム色彩関数を作成"""
        
        def color_function(word, font_size, position, orientation, random_state=None, **kwargs):
            """単語に基づいてカスタム色を決定
            
            Args:
                word: 単語
                font_size: フォントサイズ
                position: 位置
                orientation: 向き
                random_state: ランダムシード
                **kwargs: その他のパラメータ
                
            Returns:
                RGB色値のタプル
            """
            # 金融重要語句は特別な色を使用
            if word in self.config.financial_weights:
                # 重要度に応じて色の強さを調整
                weight = self.config.financial_weights[word]
                
                if weight >= 2.5:
                    # 高重要度: 赤系
                    return f"rgb({min(255, int(200 + weight * 10))}, 50, 50)"
                elif weight >= 2.0:
                    # 中重要度: オレンジ系
                    return f"rgb(255, {min(255, int(100 + weight * 30))}, 50)"
                else:
                    # 低重要度: 青系
                    return f"rgb(50, 100, {min(255, int(150 + weight * 50))})"
            
            # 一般語句は頻度に応じた色
            # フォントサイズが大きいほど濃い色
            intensity = min(255, int(100 + font_size * 2))
            
            # 色相をランダムに選択（青〜緑系を中心に）
            if random_state:
                np.random.seed(random_state)
            
            hue_choices = [
                f"rgb(50, {intensity}, 200)",      # 青系
                f"rgb(50, {intensity}, 150)",      # 青緑系  
                f"rgb(100, {intensity}, 100)",     # 緑系
                f"rgb(150, {intensity}, 50)",      # 黄緑系
            ]
            
            # ランダム選択をインデックスベースで行う
            choice_index = np.random.randint(0, len(hue_choices))
            return hue_choices[choice_index]
        
        return color_function
    
    def _wordcloud_to_base64(self, wordcloud: WordCloud) -> str:
        """WordCloudオブジェクトをbase64文字列に変換
        
        Args:
            wordcloud: WordCloudオブジェクト
            
        Returns:
            base64エンコードされた画像文字列
        """
        # matplotlibを使用して画像を生成
        plt.figure(figsize=(self.config.width/100, self.config.height/100))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        
        # バッファに保存
        buffer = io.BytesIO()
        plt.savefig(
            buffer, 
            format='PNG', 
            bbox_inches='tight', 
            dpi=100,
            facecolor='white',
            edgecolor='none'
        )
        plt.close()
        
        # base64エンコード
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        
        return image_base64
    
    def _calculate_image_quality(self, wordcloud: WordCloud, 
                               word_frequencies: Dict[str, int], 
                               image_size_bytes: int) -> float:
        """画像品質スコアを計算
        
        Args:
            wordcloud: WordCloudオブジェクト
            word_frequencies: 単語頻度辞書
            image_size_bytes: 画像サイズ（バイト）
            
        Returns:
            品質スコア（0-100）
        """
        try:
            score = 0.0
            
            # 1. 画像サイズ効率性（0-30点）
            max_size_bytes = self.config.max_file_size_kb * 1024
            if image_size_bytes <= max_size_bytes:
                size_score = 30 - (image_size_bytes / max_size_bytes) * 10
                score += max(size_score, 20)
            else:
                score += 10  # サイズオーバーペナルティ
            
            # 2. 単語配置効率性（0-25点）
            try:
                # WordCloudの内部配置情報を取得
                layout = wordcloud.layout_
                if layout:
                    placed_words = len(layout)
                    target_words = min(len(word_frequencies), self.config.max_words)
                    if target_words > 0:
                        placement_ratio = placed_words / target_words
                        placement_score = placement_ratio * 25
                        score += placement_score
                    else:
                        score += 15  # デフォルトスコア
                else:
                    score += 15  # レイアウト情報が無い場合
            except:
                score += 15  # エラー時のデフォルトスコア
            
            # 3. フォントサイズ分布（0-20点）
            if hasattr(wordcloud, 'layout_') and wordcloud.layout_:
                try:
                    font_sizes = [item[1] for item in wordcloud.layout_]
                    if font_sizes:
                        size_range = max(font_sizes) - min(font_sizes)
                        expected_range = self.config.font_size_max - self.config.font_size_min
                        if expected_range > 0:
                            range_ratio = min(size_range / expected_range, 1.0)
                            range_score = range_ratio * 20
                            score += range_score
                        else:
                            score += 10
                    else:
                        score += 10
                except:
                    score += 10
            else:
                score += 10
            
            # 4. 色彩多様性（0-15点）
            # 簡易的な評価: 金融重要語句の含有率
            financial_words = sum(1 for word in word_frequencies.keys() 
                                if word in self.config.financial_weights)
            total_words = len(word_frequencies)
            if total_words > 0:
                diversity_ratio = financial_words / total_words
                diversity_score = min(diversity_ratio * 15, 15)
                score += diversity_score
            
            # 5. 全体バランス（0-10点）
            # 単語数と画像サイズのバランス
            words_per_pixel = len(word_frequencies) / (self.config.width * self.config.height)
            optimal_density = 0.0001  # 最適密度の目安
            
            if words_per_pixel <= optimal_density * 2:
                density_score = 10 - abs(words_per_pixel - optimal_density) * 50000
                score += max(density_score, 5)
            else:
                score += 3  # 過密ペナルティ
            
            return min(score, 100.0)
            
        except Exception as e:
            print(f"画像品質計算エラー: {e}")
            return 60.0  # デフォルトスコア
    
    def optimize_image_quality(self, wordcloud: WordCloud) -> WordCloud:
        """画像品質を最適化（将来の拡張用）
        
        Args:
            wordcloud: 元のWordCloudオブジェクト
            
        Returns:
            最適化されたWordCloudオブジェクト
        """
        # 現在は元のオブジェクトをそのまま返す
        # 将来的にはガウシアンフィルタ、シャープ化等を適用
        return wordcloud