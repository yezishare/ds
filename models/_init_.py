from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.Enum('draft', 'published', 'unpublished'), 
                      default='draft', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                          onupdate=datetime.utcnow)
    
    # 关系
    main_images = db.relationship('ProductImage', 
                                primaryjoin="and_(ProductImage.product_id==Product.id, "
                                           "ProductImage.type=='main')",
                                lazy='dynamic',
                                order_by='ProductImage.sort_order')
    detail_images = db.relationship('ProductImage', 
                                  primaryjoin="and_(ProductImage.product_id==Product.id, "
                                             "ProductImage.type=='detail')",
                                  lazy='dynamic',
                                  order_by='ProductImage.sort_order')
    videos = db.relationship('ProductVideo', backref='product', lazy=True)
    analytics = db.relationship('ProductAnalytics', backref='product', uselist=False)
    events = db.relationship('UserEvent', backref='product', lazy='dynamic')

class ProductImage(db.Model):
    __tablename__ = 'product_images'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    type = db.Column(db.Enum('main', 'detail'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductVideo(db.Model):
    __tablename__ = 'product_videos'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    duration = db.Column(db.Integer)  # 视频时长(秒)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.String(64), primary_key=True, default=generate_uuid)
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    referrer = db.Column(db.String(500))
    landing_page = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=0)
    
    events = db.relationship('UserEvent', backref='session', lazy='dynamic')
    profile = db.relationship('UserBehaviorProfile', backref='session', uselist=False)

class UserEvent(db.Model):
    __tablename__ = 'user_events'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('user_sessions.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    event_data = db.Column(db.JSON)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.Index('idx_session_event', 'session_id', 'event_type'),
        db.Index('idx_timestamp', 'timestamp'),
        db.Index('idx_product_events', 'product_id', 'event_type'),
    )

class UserBehaviorProfile(db.Model):
    __tablename__ = 'user_behavior_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('user_sessions.id'), unique=True)
    interest_categories = db.Column(db.JSON)
    engagement_score = db.Column(db.Float, default=0.0)
    behavior_pattern = db.Column(db.String(50))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class ProductAnalytics(db.Model):
    __tablename__ = 'product_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), unique=True)
    view_count = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)
    video_play_count = db.Column(db.Integer, default=0)
    avg_engagement_time = db.Column(db.Float, default=0.0)
    conversion_rate = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
