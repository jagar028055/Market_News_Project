# Market News Project - 統合API仕様書
## パーソナライゼーション機能完全対応版

**バージョン**: v1.4.0  
**最終更新**: 2025-08-15  
**対応機能**: Flash+Pro + パーソナライゼーション

---

## 🎯 パーソナライゼーション API

### 1. ユーザー別配信最適化 API

#### ユーザープロファイル管理
```python
from src.personalization.user_optimizer import UserOptimizer

optimizer = UserOptimizer()

# ユーザープロファイル作成
profile = optimizer.create_user_profile("user_001", {
    'interests': ['technology', 'finance'],
    'reading_time': 'morning',
    'frequency': 5,
    'device_type': 'mobile',
    'language': 'ja'
})

# プロファイル取得
user_profile = optimizer.get_user_profile("user_001")

# 最適コンテンツ推奨
recommendations = optimizer.optimize_content_for_user("user_001", available_content)
```

#### ユーザー行動記録
```python
# エンゲージメント記録
optimizer.record_user_interaction("user_001", "article_123", "share", session_duration=180)

# 最適配信時間取得
optimal_time = optimizer.get_optimal_delivery_time("user_001")

# 分析データ取得
analytics = optimizer.get_user_analytics("user_001", days=30)
```

### 2. AI駆動コンテンツ推奨 API

#### コンテンツベクトル化
```python
from src.personalization.ai_recommender import AIContentRecommender

recommender = AIContentRecommender()

# コンテンツベクトル化
content_vector = recommender.vectorize_content({
    'id': 'article_001',
    'title': '最新AI技術トレンド',
    'summary': 'AI技術の最新動向...',
    'categories': ['technology', 'ai'],
    'published_at': datetime.now().isoformat(),
    'views': 1500, 'shares': 25, 'comments': 8
})

# コンテンツ推奨実行
recommendations = recommender.recommend_content("user_001", available_content, top_k=10)
```

#### ユーザーベクトル構築
```python
# インタラクション履歴からユーザーベクトル構築
user_vector = recommender.build_user_vector("user_001", interaction_history)

# フィードバック記録
recommender.record_recommendation_feedback("user_001", "article_001", 
                                         recommended_score=0.85, 
                                         actual_engagement=0.75)
```

### 3. 動的ユーザーセグメンテーション API

#### セグメンテーション実行
```python
from src.personalization.user_segmentation import DynamicUserSegmentation

segmentation = DynamicUserSegmentation()

# ユーザーセグメント割り当て
assigned_segment = segmentation.segment_user("user_001", interaction_history)

# セグメント情報取得
segment_info = segmentation.get_user_segment_info("user_001")

# セグメント内ユーザー一覧
segment_users = segmentation.get_segment_users("power_users")
```

#### セグメンテーション分析
```python
# 全体指標計算
metrics = segmentation.calculate_segmentation_metrics()

# 行動パターン分析
behavior_patterns = segmentation.analyze_user_behavior("user_001", interaction_history)
```

### 4. 予測分析 API

#### エンゲージメント予測
```python
from src.personalization.predictive_analytics import PredictiveAnalytics

analytics = PredictiveAnalytics()

# エンゲージメント予測
engagement_prediction = analytics.predict_user_engagement("user_001", interaction_history)

# チャーン率予測
churn_prediction = analytics.predict_churn_risk("user_001", interaction_history)

# コンテンツ需要予測
demand_prediction = analytics.predict_content_demand("technology", historical_metrics)
```

#### 時系列分析
```python
# トレンド分析
trend_analysis = analytics.analyze_time_series_trend(time_series_data)

# 予測結果保存・取得
analytics.save_prediction(prediction_result)
user_predictions = analytics.get_user_predictions("user_001")
```

### 5. インテリジェント配信タイミング最適化 API

#### タイミング最適化
```python
from src.personalization.timing_optimizer import IntelligentTimingOptimizer, DeliveryChannel

optimizer = IntelligentTimingOptimizer()

# 最適配信タイミング計算
optimal_timing = optimizer.optimize_delivery_timing(
    user_id="user_001",
    content_type="news",
    interaction_history=interaction_history,
    preferred_channels=[DeliveryChannel.PUSH, DeliveryChannel.EMAIL],
    urgency_level="normal"
)

# 配信パフォーマンス記録
performance = DeliveryPerformance(
    delivery_id="delivery_001",
    user_id="user_001",
    scheduled_time=datetime.now(),
    actual_delivery_time=datetime.now(),
    opened_time=datetime.now() + timedelta(minutes=5),
    engagement_time=datetime.now() + timedelta(minutes=8),
    engagement_score=0.75,
    channel=DeliveryChannel.PUSH
)
optimizer.record_delivery_performance(performance)
```

#### タイミング分析
```python
# ユーザータイミングパターン分析
timing_patterns = optimizer.analyze_user_timing_patterns("user_001", interaction_history)

# 配信時間窓計算
delivery_windows = optimizer.calculate_delivery_windows("user_001", timing_patterns)

# 分析データ取得
timing_analytics = optimizer.get_user_timing_analytics("user_001")
```

---

## 💾 データ形式仕様

### パーソナライゼーション共通データ型

#### UserProfile
```python
@dataclass
class UserProfile:
    user_id: str
    interests: List[str]
    reading_time_preference: str  # morning, afternoon, evening, night
    frequency_preference: int  # 1日あたりの配信希望数
    engagement_score: float  # 0.0-1.0
    device_type: str  # mobile, desktop, tablet
    language: str  # ja, en
    created_at: datetime
    updated_at: datetime
```

#### ContentRecommendation
```python
@dataclass
class ContentRecommendation:
    content_id: str
    score: float  # 関連度スコア 0.0-1.0
    reason: str  # 推奨理由
    categories: List[str]
    estimated_read_time: int  # 推定読了時間（秒）
```

#### PredictionResult
```python
@dataclass
class PredictionResult:
    prediction_id: str
    user_id: Optional[str]
    prediction_type: PredictionType  # ENGAGEMENT, CHURN_RISK, CONTENT_DEMAND
    predicted_value: float
    confidence_level: float
    prediction_date: datetime
    valid_until: datetime
    contributing_factors: Dict[str, float]
    model_version: str
```

#### OptimalTiming
```python
@dataclass
class OptimalTiming:
    user_id: str
    content_type: str
    recommended_time: datetime
    confidence_score: float
    strategy: TimingStrategy  # OPTIMAL_ENGAGEMENT, IMMEDIATE, SCHEDULED, ADAPTIVE
    delivery_windows: List[DeliveryWindow]
    fallback_times: List[datetime]
    reasoning: Dict[str, Any]
```

---

## 🔧 コアAPI (既存機能)

### ProSummarizer API

#### 地域別要約生成
```python
from ai_pro_summarizer import ProSummarizer

summarizer = ProSummarizer(api_key="your_api_key")
regional_summaries = summarizer.generate_regional_summaries(grouped_articles)
```

**入力:**
- grouped_articles: Dict[str, List[Dict]] - 地域別グループ化された記事

**出力:**
- Dict[str, Dict] - 地域別要約結果

#### 全体要約生成
```python
global_summary = summarizer.generate_global_summary(all_articles, regional_summaries)
```

### ArticleGrouper API

#### 地域別グループ化
```python
from article_grouper import ArticleGrouper

grouper = ArticleGrouper()
grouped = grouper.group_articles_by_region(articles)
```

### CostManager API

#### コスト見積もり
```python
from cost_manager import CostManager

cost_manager = CostManager()
estimated_cost = cost_manager.estimate_cost(model_name, input_text, output_tokens)
```

## データ形式

### 記事データ形式
- title: 記事タイトル
- body: 記事本文  
- source: 情報源
- url: 記事URL
- published_at: 公開日時
- region: 地域分類
- category: カテゴリ分類

### 要約結果形式
- global_summary: 全体市況要約
- regional_summaries: 地域別要約辞書
- metadata: メタデータ（記事数など）

---
更新日: 2025-08-13
