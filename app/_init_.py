import numpy as np
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BehaviorAnalyzer:
    def __init__(self):
        self.engagement_weights = {
            'session_duration': 0.2,
            'total_events': 0.15,
            'product_views': 0.2,
            'image_clicks': 0.15,
            'video_plays': 0.2,
            'unique_products': 0.1
        }
    
    def extract_session_features(self, session):
        """提取会话特征（简化版，避免复杂的机器学习依赖）"""
        try:
            events = session.events.all()
            
            features = {
                'session_duration': session.duration or 0,
                'total_events': len(events),
                'product_views': len([e for e in events if e.event_type == 'product_view']),
                'image_clicks': len([e for e in events if e.event_type == 'image_click']),
                'video_plays': len([e for e in events if e.event_type == 'video_play']),
                'unique_products': len(set(e.product_id for e in events if e.product_id)),
                'avg_time_per_event': session.duration / len(events) if events else 0
            }
            
            return features
        except Exception as e:
            logger.error(f"Error extracting session features: {e}")
            return {}
    
    def analyze_behavior_pattern(self, session):
        """分析用户行为模式（简化版）"""
        try:
            features = self.extract_session_features(session)
            if not features:
                return self._get_default_analysis()
            
            # 基于规则的行为模式分类（避免机器学习依赖）
            engagement_score = self._calculate_engagement_score(features)
            behavior_pattern = self._classify_behavior_pattern(features, engagement_score)
            
            return {
                'behavior_pattern': behavior_pattern,
                'engagement_score': engagement_score,
                'interest_categories': self._extract_interests(session),
                'features': features
            }
        except Exception as e:
            logger.error(f"Error analyzing behavior: {e}")
            return self._get_default_analysis()
    
    def _calculate_engagement_score(self, features):
        """计算参与度评分"""
        try:
            score = 0
            max_values = {
                'session_duration': 300,  # 5分钟
                'total_events': 20,
                'product_views': 10,
                'image_clicks': 15,
                'video_plays': 5,
                'unique_products': 8
            }
            
            for feature, weight in self.engagement_weights.items():
                max_val = max_values.get(feature, 1)
                normalized_value = min(features[feature] / max_val, 1.0)
                score += normalized_value * weight
            
            return round(score * 100, 2)
        except Exception as e:
            logger.error(f"Error calculating engagement score: {e}")
            return 50.0
    
    def _classify_behavior_pattern(self, features, engagement_score):
        """基于规则的行为模式分类"""
        if engagement_score >= 80:
            return 'high_engagement'
        elif engagement_score >= 50:
            if features.get('video_plays', 0) > 2:
                return 'video_interested'
            elif features.get('unique_products', 0) > 5:
                return 'browsing_intensive'
            else:
                return 'moderate_engagement'
        else:
            if features.get('session_duration', 0) < 30:
                return 'bounce'
            else:
                return 'low_engagement'
    
    def _extract_interests(self, session):
        """提取用户兴趣"""
        try:
            product_views = session.events.filter_by(event_type='product_view').all()
            product_ids = [e.product_id for e in product_views if e.product_id]
            
            return {
                'viewed_products': product_ids[:10],  # 限制数量
                'total_views': len(product_ids),
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error extracting interests: {e}")
            return {'viewed_products': [], 'total_views': 0}
    
    def _get_default_analysis(self):
        """获取默认分析结果"""
        return {
            'behavior_pattern': 'unknown',
            'engagement_score': 0.0,
            'interest_categories': {'viewed_products': [], 'total_views': 0}
        }

class RealTimeRecommender:
    def __init__(self):
        self.analyzer = BehaviorAnalyzer()
    
    def get_personalized_recommendations(self, session, current_product_id=None, limit=5):
        """获取个性化推荐（简化版）"""
        try:
            # 获取用户浏览历史
            viewed_products = self._get_viewed_products(session)
            
            if not viewed_products:
                return self._get_popular_recommendations(limit)
            
            # 排除当前产品和已浏览产品
            excluded_ids = set(viewed_products)
            if current_product_id:
                excluded_ids.add(current_product_id)
            
            # 基于浏览历史的简单推荐
            recommendations = self._get_similar_products(viewed_products, excluded_ids, limit)
            
            return recommendations if recommendations else self._get_popular_recommendations(limit)
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return self._get_popular_recommendations(limit)
    
    def _get_viewed_products(self, session):
        """获取用户浏览过的商品"""
        from models import UserEvent
        events = UserEvent.query.filter_by(
            session_id=session.id, 
            event_type='product_view'
        ).all()
        return list(set(e.product_id for e in events if e.product_id))
    
    def _get_similar_products(self, viewed_products, excluded_ids, limit):
        """获取相似商品（基于简单的关联规则）"""
        from models import UserEvent, Product
        try:
            # 查找也浏览了这些商品的其他用户还浏览了什么
            similar_sessions = UserEvent.query.filter(
                UserEvent.event_type == 'product_view',
                UserEvent.product_id.in_(viewed_products),
                UserEvent.session_id != None
            ).distinct(UserEvent.session_id).limit(100).all()
            
            session_ids = set(e.session_id for e in similar_sessions)
            
            # 获取这些会话浏览的其他商品
            recommended_products = UserEvent.query.filter(
                UserEvent.event_type == 'product_view',
                UserEvent.session_id.in_(session_ids),
                ~UserEvent.product_id.in_(excluded_ids),
                UserEvent.product_id != None
            ).group_by(UserEvent.product_id).order_by(
                db.func.count(UserEvent.id).desc()
            ).limit(limit).all()
            
            return [e.product_id for e in recommended_products]
        except Exception as e:
            logger.error(f"Error finding similar products: {e}")
            return []
    
    def _get_popular_recommendations(self, limit):
        """获取热门推荐"""
        from models import ProductAnalytics, Product
        try:
            popular = ProductAnalytics.query.join(Product).filter(
                Product.status == 'published'
            ).order_by(
                ProductAnalytics.view_count.desc()
            ).limit(limit).all()
            
            return [pa.product_id for pa in popular]
        except Exception as e:
            logger.error(f"Error getting popular recommendations: {e}")
            return []
