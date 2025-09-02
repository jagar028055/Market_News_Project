"""
DialogueScriptGenerator のユニットテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.podcast.script_generator import DialogueScriptGenerator, ArticlePriority


class TestDialogueScriptGenerator:
    """DialogueScriptGenerator のテストクラス"""
    
    @pytest.fixture
    def mock_config(self):
        """設定のモック"""
        config = Mock()
        config.podcast.target_character_count = (2400, 2800)
        config.podcast.load_pronunciation_dict.return_value = {
            "FRB": "エフアールビー",
            "NASDAQ": "ナスダック",
            "GDP": "ジーディーピー"
        }
        return config
    
    @pytest.fixture
    def sample_articles(self):
        """テスト用記事データ"""
        return [
            {
                'title': 'FRB、利上げ継続の方針',
                'content': 'アメリカの中央銀行であるFRBが政策金利の利上げを継続する方針を発表しました。',
                'summary': 'FRBが利上げ継続方針を発表',
                'published': '2024-01-15T09:00:00Z'
            },
            {
                'title': 'NASDAQ、過去最高値を更新',
                'content': 'テクノロジー株の急騰により、NASDAQ総合指数が過去最高値を更新しました。',
                'summary': 'NASDAQ指数が最高値更新',
                'published': '2024-01-15T10:00:00Z'
            },
            {
                'title': 'GDP成長率、予想上回る',
                'content': '第4四半期のGDP成長率が市場予想を上回りました。',
                'summary': 'GDP成長率が予想上回る',
                'published': '2024-01-15T11:00:00Z'
            }
        ]
    
    @pytest.fixture
    def generator(self, mock_config):
        """DialogueScriptGenerator インスタンス"""
        with patch('src.podcast.script_generator.get_config', return_value=mock_config):
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel'):
                    return DialogueScriptGenerator("test_api_key")
    
    def test_init(self, generator):
        """初期化のテスト"""
        assert generator.api_key == "test_api_key"
        assert generator.model_name == "gemini-2.0-flash-exp"
        assert generator.target_char_min == 2400
        assert generator.target_char_max == 2800
        assert "FRB" in generator.pronunciation_dict
    
    def test_prioritize_articles(self, generator, sample_articles):
        """記事の優先度付けテスト"""
        prioritized = generator._prioritize_articles(sample_articles)
        
        # 3つの記事が返される
        assert len(prioritized) == 3
        
        # ArticlePriority オブジェクトが返される
        assert all(isinstance(article, ArticlePriority) for article in prioritized)
        
        # 優先度順にソートされている（高い順）
        scores = [article.priority_score for article in prioritized]
        assert scores == sorted(scores, reverse=True)
        
        # FRBを含む記事が高優先度
        frb_article = next((a for a in prioritized if 'FRB' in a.title), None)
        assert frb_article is not None
        assert frb_article.priority_score > 0
    
    def test_calculate_priority(self, generator):
        """優先度計算のテスト"""
        # 高優先度キーワードを含む記事
        high_priority_article = {
            'title': 'FRB政策金利発表',
            'content': '日銀の政策決定会合でも注目されています。',
            'published': '2024-01-15T09:00:00Z'
        }
        
        # 中優先度キーワードを含む記事
        medium_priority_article = {
            'title': '企業決算発表',
            'content': '今期の業績予想について発表しました。',
            'published': '2024-01-15T09:00:00Z'
        }
        
        # 無関係な記事
        low_priority_article = {
            'title': '天気予報',
            'content': '今日は晴れの予報です。',
            'published': '2024-01-15T09:00:00Z'
        }
        
        high_score = generator._calculate_priority(high_priority_article)
        medium_score = generator._calculate_priority(medium_priority_article)
        low_score = generator._calculate_priority(low_priority_article)
        
        assert high_score > medium_score > low_score
    
    def test_categorize_article(self, generator):
        """記事カテゴリ分類のテスト"""
        test_cases = [
            ({'title': 'FRB利上げ', 'content': '金利政策'}, '金融政策'),
            ({'title': '株価上昇', 'content': '日経平均'}, '株式市場'),
            ({'title': '円安進行', 'content': 'ドル円'}, '為替'),
            ({'title': '企業決算', 'content': '売上増加'}, '企業業績'),
            ({'title': '一般ニュース', 'content': '経済動向'}, '一般経済')
        ]
        
        for article, expected_category in test_cases:
            category = generator._categorize_article(article)
            assert category == expected_category
    
    def test_format_dialogue_with_existing_tags(self, generator):
        """既存タグがある台本のフォーマットテスト"""
        raw_script = """<speaker1>田中</speaker1>: おはようございます。
<speaker2>山田</speaker2>: おはようございます。今日のニュースをお伝えします。"""
        
        formatted = generator._format_dialogue(raw_script)
        
        assert '<speaker1>' in formatted
        assert '<speaker2>' in formatted
        assert '田中' in formatted
        assert '山田' in formatted
    
    def test_format_dialogue_without_tags(self, generator):
        """タグがない台本のフォーマットテスト"""
        raw_script = """田中: おはようございます。
山田: おはようございます。今日のニュースをお伝えします。
田中: まず最初のニュースからです。"""
        
        formatted = generator._format_dialogue(raw_script)
        
        assert '<speaker1>' in formatted
        assert '<speaker2>' in formatted
        assert formatted.count('<speaker1>') >= 2
        assert formatted.count('<speaker2>') >= 1
    
    def test_apply_pronunciation_corrections(self, generator):
        """発音修正のテスト"""
        script = "今日はFRBの発表があり、NASDAQも上昇しました。GDPの発表も注目されています。"
        
        corrected = generator._apply_pronunciation_corrections(script)
        
        assert "FRB" not in corrected
        assert "エフアールビー" in corrected
        assert "NASDAQ" not in corrected
        assert "ナスダック" in corrected
        assert "GDP" not in corrected
        assert "ジーディーピー" in corrected
    
    def test_normalize_speaker_tags(self, generator):
        """スピーカータグ正規化のテスト"""
        malformed_script = """<speaker1>田中</speaker2>: おはようございます。
<speaker2>山田:</speaker2>: こんにちは。"""
        
        normalized = generator._normalize_speaker_tags(malformed_script)
        
        # 基本的な構造が保たれている
        assert '<speaker1>' in normalized
        assert '<speaker2>' in normalized
    
    def test_trim_script(self, generator):
        """台本短縮のテスト"""
        # 長すぎる台本を作成
        long_script = "あ" * 3000  # 3000文字
        
        trimmed = generator._trim_script(long_script)
        
        # 目標文字数以下になっている
        assert len(trimmed) <= generator.target_char_max
    
    def test_create_script_prompt(self, generator, sample_articles):
        """台本生成プロンプト作成のテスト"""
        prioritized_articles = generator._prioritize_articles(sample_articles)
        prompt = generator._create_script_prompt(prioritized_articles)
        
        # プロンプトに必要な要素が含まれている
        assert "台本を作成" in prompt
        assert "2人のホスト" in prompt
        assert "田中さんと山田さん" in prompt
        assert "2,400〜2,800文字" in prompt
        assert "<speaker1>" in prompt
        assert "<speaker2>" in prompt
        
        # 記事内容が含まれている
        assert "FRB" in prompt
        assert "NASDAQ" in prompt
        assert "GDP" in prompt
    
    @patch('google.generativeai.GenerativeModel')
    def test_generate_script_success(self, mock_model_class, generator, sample_articles):
        """台本生成成功のテスト"""
        # モックの設定
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = """<speaker1>田中</speaker1>: おはようございます。今日のマーケットニュースをお伝えします。
<speaker2>山田</speaker2>: おはようございます。まず最初にFRBの利上げについてお話しします。
<speaker1>田中</speaker1>: そうですね。エフアールビーが政策金利の利上げを継続する方針を発表しました。これにより市場にどのような影響があるでしょうか。
<speaker2>山田</speaker2>: 利上げは通常、株式市場には下押し圧力となりますが、今回は市場の予想通りだったため、大きな変動は見られませんでした。
<speaker1>田中</speaker1>: 次にNASDAQの動向についてです。テクノロジー株の急騰により最高値を更新しました。
<speaker2>山田</speaker2>: ナスダックの上昇は特にAI関連株が牽引しています。投資家の関心が高まっていることがうかがえます。
<speaker1>田中</speaker1>: 最後にGDPについてです。第4四半期の成長率が予想を上回りました。
<speaker2>山田</speaker2>: ジーディーピーの好調な数字は経済の底堅さを示しており、今後の金融政策にも影響を与える可能性があります。
<speaker1>田中</speaker1>: 本日のマーケットニュースは以上です。ありがとうございました。
<speaker2>山田</speaker2>: ありがとうございました。また明日お会いしましょう。"""
        
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        generator.model = mock_model
        
        # 台本生成実行
        result = generator.generate_script(sample_articles)
        
        # 結果の検証
        assert isinstance(result, str)
        assert len(result) > 0
        assert '<speaker1>' in result
        assert '<speaker2>' in result
        assert 'エフアールビー' in result  # 発音修正が適用されている
        assert 'ナスダック' in result     # 発音修正が適用されている
        assert 'ジーディーピー' in result  # 発音修正が適用されている
        
        # 文字数が適切範囲内
        char_count = len(result)
        assert generator.target_char_min <= char_count <= generator.target_char_max or char_count < generator.target_char_min  # 短すぎる場合は警告のみ
    
    @patch('google.generativeai.GenerativeModel')
    def test_generate_script_api_error(self, mock_model_class, generator, sample_articles):
        """台本生成APIエラーのテスト"""
        # モックの設定（API エラー）
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model
        generator.model = mock_model
        
        # エラーが発生することを確認
        with pytest.raises(Exception) as exc_info:
            generator.generate_script(sample_articles)
        
        assert "API Error" in str(exc_info.value) or "台本生成に失敗" in str(exc_info.value)
    
    def test_character_count_limits(self, generator):
        """文字数制限のテスト"""
        # 短すぎる台本
        short_script = "短い台本です。"
        result_short = generator._trim_script(short_script)
        assert len(result_short) == len(short_script)  # 短い場合はそのまま
        
        # 適切な長さの台本
        normal_script = "あ" * 2600  # 適切な長さ
        result_normal = generator._trim_script(normal_script)
        assert len(result_normal) == len(normal_script)  # 適切な場合はそのまま
        
        # 長すぎる台本
        long_script = "あ" * 3000  # 長すぎる
        result_long = generator._trim_script(long_script)
        assert len(result_long) <= generator.target_char_max  # 短縮される
    
    def test_speaker_tag_format(self, generator):
        """スピーカータグ形式のテスト"""
        test_scripts = [
            "田中: こんにちは",
            "山田: こんばんは",
            "A: テストです",
            "B: 確認です",
            "ホスト1: 始まります",
            "ホスト2: 終わります"
        ]
        
        for script in test_scripts:
            formatted = generator._format_dialogue(script)
            assert '<speaker' in formatted
            assert '</speaker' in formatted
            assert ':' in formatted