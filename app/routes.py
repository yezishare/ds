from flask import Blueprint, request, jsonify, send_from_directory, render_template, g
from models import db, Product, ProductImage, ProductVideo, UserSession, UserEvent, UserBehaviorProfile, ProductAnalytics
from ai_agent.behavior_analyzer import BehaviorAnalyzer, RealTimeRecommender
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

# 初始化AI组件
behavior_analyzer = BehaviorAnalyzer()
recommender = RealTimeRecommender()

main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__)
api_bp = Blueprint('api', __name__)

# 中间件
@api_bp.before_request
def track_session():
    """会话跟踪中间件"""
    session_id = request.cookies.get('session_id') or request.headers.get('X-Session-ID')
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    session = UserSession.query.get(session_id)
    if not session:
        session = UserSession(
            id=session_id,
            user_agent=request.headers.get('User-Agent'),
            ip_address=request.remote_addr,
            referrer=request.headers.get('Referer'),
            landing_page=request.path
        )
        db.session.add(session)
        db.session.commit()
    
    g.session = session
    g.session_id = session_id

@api_bp.after_request
def update_session(response):
    """更新会话信息"""
    if hasattr(g, 'session'):
        g.session.last_activity = datetime.utcnow()
        db.session.commit()
        response.set_cookie('session_id', g.session_id, max_age=3600*24*7)
    return response

# 工具函数
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def product_to_dict(product):
    """商品数据序列化"""
    return {
        'id': product.id,
        'title': product.title,
        'description': product.description,
        'status': product.status,
        'main_images': [
            {'id': img.id, 'url': f'/api/files/images/{img.id}', 'filename': img.filename}
            for img in product.main_images
        ],
        'videos': [
            {'id': video.id, 'url': f'/api/files/videos/{video.id}', 'filename': video.filename}
            for video in product.videos
        ],
        'detail_images': [
            {'id': img.id, 'url': f'/api/files/images/{img.id}', 'filename': img.filename}
            for img in product.detail_images
        ],
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'updated_at': product.updated_at.isoformat() if product.updated_at else None
    }

# 前端路由
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    return render_template('product_detail.html', product_id=product_id)

# 管理后台路由
@admin_bp.route('/')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/products')
def admin_products():
    return render_template('admin/products.html')

@admin_bp.route('/analytics')
def admin_analytics():
    return render_template('admin/analytics.html')

# API路由
@api_bp.route('/products', methods=['GET'])
def get_products():
    """获取商品列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        search = request.args.get('search', '')
        
        query = Product.query.filter_by(status='published')
        
        if search:
            query = query.filter(Product.title.ilike(f'%{search}%'))
        
        products = query.order_by(Product.updated_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'products': [product_to_dict(p) for p in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """获取单个商品详情"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # 记录商品查看事件
        event = UserEvent(
            session_id=g.session_id,
            event_type='product_view',
            product_id=product_id,
            event_data={'page': 'product_detail'}
        )
        db.session.add(event)
        
        # 更新商品分析数据
        analytics = ProductAnalytics.query.filter_by(product_id=product_id).first()
        if not analytics:
            analytics = ProductAnalytics(product_id=product_id)
            db.session.add(analytics)
        analytics.view_count += 1
        analytics.last_updated = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify(product_to_dict(product))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/events', methods=['POST'])
def track_event():
    """收集用户行为事件"""
    try:
        data = request.json
        event_type = data.get('event_type')
        product_id = data.get('product_id')
        event_data = data.get('event_data', {})
        
        event = UserEvent(
            session_id=g.session_id,
            event_type=event_type,
            product_id=product_id,
            event_data=event_data
        )
        db.session.add(event)
        
        # 更新会话时长
        if event_type == 'session_end':
            g.session.duration = event_data.get('total_time', 0)
        
        # 实时行为分析（每5个事件分析一次）
        event_count = UserEvent.query.filter_by(session_id=g.session_id).count()
        if event_count % 5 == 0:
            analysis_result = behavior_analyzer.analyze_behavior_pattern(g.session)
            
            profile = UserBehaviorProfile.query.filter_by(session_id=g.session_id).first()
            if not profile:
                profile = UserBehaviorProfile(session_id=g.session_id)
                db.session.add(profile)
            
            profile.interest_categories = analysis_result['interest_categories']
            profile.engagement_score = analysis_result['engagement_score']
            profile.behavior_pattern = analysis_result['behavior_pattern']
            profile.last_updated = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'message': 'Event recorded', 'event_id': event.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/products/<int:product_id>/recommendations')
def get_recommendations(product_id):
    """获取商品推荐"""
    try:
        recommended_ids = recommender.get_personalized_recommendations(
            g.session, product_id, limit=5
        )
        
        recommended_products = Product.query.filter(
            Product.id.in_(recommended_ids),
            Product.status == 'published'
        ).all()
        
        return jsonify({
            'recommendations': [product_to_dict(p) for p in recommended_products]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/files/images/<int:image_id>')
def serve_image(image_id):
    """提供图片文件"""
    image = ProductImage.query.get_or_404(image_id)
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'images'),
        image.filename
    )

@api_bp.route('/files/videos/<int:video_id>')
def serve_video(video_id):
    """提供视频文件"""
    video = ProductVideo.query.get_or_404(video_id)
    return send_from_directory(
        os.path.join(current_app.config['UPLOAD_FOLDER'], 'videos'),
        video.filename
    )

# 管理员API
@api_bp.route('/admin/products', methods=['GET'])
def get_admin_products():
    """管理员获取商品列表"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        query = Product.query
        if search:
            query = query.filter(Product.title.ilike(f'%{search}%'))
        
        products = query.order_by(Product.updated_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return jsonify({
            'products': [product_to_dict(p) for p in products.items],
            'total': products.total,
            'pages': products.pages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/products', methods=['POST'])
def create_product():
    """创建商品"""
    try:
        data = request.form
        title = data.get('title')
        
        if not title:
            return jsonify({'error': '商品标题不能为空'}), 400
        
        product = Product(
            title=title,
            description=data.get('description', ''),
            status='draft'
        )
        db.session.add(product)
        db.session.flush()  # 获取product.id
        
        # 处理主图上传
        main_images = request.files.getlist('main_images')
        for i, image in enumerate(main_images[:10]):
            if image and allowed_file(image.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
                filename = secure_filename(f"{product.id}_main_{i}_{image.filename}")
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', filename)
                image.save(filepath)
                
                product_image = ProductImage(
                    product_id=product.id,
                    type='main',
                    filename=filename,
                    filepath=filepath,
                    sort_order=i
                )
                db.session.add(product_image)
        
        # 处理详情图上传
        detail_images = request.files.getlist('detail_images')
        for i, image in enumerate(detail_images):
            if image and allowed_file(image.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
                filename = secure_filename(f"{product.id}_detail_{i}_{image.filename}")
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'images', filename)
                image.save(filepath)
                
                product_image = ProductImage(
                    product_id=product.id,
                    type='detail',
                    filename=filename,
                    filepath=filepath,
                    sort_order=i
                )
                db.session.add(product_image)
        
        # 处理视频上传
        video = request.files.get('video')
        if video and allowed_file(video.filename, current_app.config['ALLOWED_VIDEO_EXTENSIONS']):
            filename = secure_filename(f"{product.id}_{video.filename}")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'videos', filename)
            video.save(filepath)
            
            product_video = ProductVideo(
                product_id=product.id,
                filename=filename,
                filepath=filepath
            )
            db.session.add(product_video)
        
        # 创建商品分析记录
        analytics = ProductAnalytics(product_id=product.id)
        db.session.add(analytics)
        
        db.session.commit()
        
        return jsonify({'message': '商品创建成功', 'product_id': product.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/products/<int:product_id>/status', methods=['PUT'])
def update_product_status(product_id):
    """更新商品状态"""
    try:
        product = Product.query.get_or_404(product_id)
        data = request.json
        status = data.get('status')
        
        if status not in ['published', 'unpublished', 'draft']:
            return jsonify({'error': '状态值无效'}), 400
        
        product.status = status
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': f'商品状态已更新为{status}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/analytics/dashboard')
def get_analytics_dashboard():
    """获取分析仪表板数据"""
    try:
        # 基础统计
        total_sessions = UserSession.query.count()
        total_events = UserEvent.query.count()
        total_products = Product.query.filter_by(status='published').count()
        
        # 今日数据
        today = datetime.utcnow().date()
        today_sessions = UserSession.query.filter(
            db.func.date(UserSession.created_at) == today
        ).count()
        
        # 热门商品
        popular_products = db.session.query(
            Product, ProductAnalytics
        ).join(ProductAnalytics).filter(
            Product.status == 'published'
        ).order_by(
            ProductAnalytics.view_count.desc()
        ).limit(5).all()
        
        # 用户行为模式分布
        behavior_patterns = db.session.query(
            UserBehaviorProfile.behavior_pattern,
            db.func.count(UserBehaviorProfile.id)
        ).group_by(UserBehaviorProfile.behavior_pattern).all()
        
        return jsonify({
            'summary': {
                'total_sessions': total_sessions,
                'total_events': total_events,
                'total_products': total_products,
                'today_sessions': today_sessions
            },
            'popular_products': [
                {
                    'product': product_to_dict(product),
                    'views': analytics.view_count,
                    'clicks': analytics.click_count
                }
                for product, analytics in popular_products
            ],
            'behavior_distribution': dict(behavior_patterns)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
