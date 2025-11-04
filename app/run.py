#!/usr/bin/env python3
import os
from app import create_app
from models import db

app = create_app('development')

@app.cli.command('init-db')
def init_db():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
    print('数据库初始化完成！')

@app.cli.command('seed-data')
def seed_data():
    """添加测试数据"""
    from models import Product, ProductImage, ProductVideo, ProductAnalytics
    from datetime import datetime
    
    with app.app_context():
        # 清空现有数据
        db.drop_all()
        db.create_all()
        
        # 添加测试商品
        products = []
        for i in range(1, 21):
            product = Product(
                title=f'测试商品 {i}',
                description=f'这是测试商品 {i} 的描述',
                status='published' if i % 2 == 0 else 'draft',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(product)
            products.append(product)
        
        db.session.flush()
        
        # 为每个商品添加图片和视频
        for i, product in enumerate(products):
            # 主图
            for j in range(3):
                main_image = ProductImage(
                    product_id=product.id,
                    type='main',
                    filename=f'test_main_{i}_{j}.jpg',
                    filepath=f'uploads/images/test_main_{i}_{j}.jpg',
                    sort_order=j
                )
                db.session.add(main_image)
            
            # 详情图
            for j in range(2):
                detail_image = ProductImage(
                    product_id=product.id,
                    type='detail',
                    filename=f'test_detail_{i}_{j}.jpg',
                    filepath=f'uploads/images/test_detail_{i}_{j}.jpg',
                    sort_order=j
                )
                db.session.add(detail_image)
            
            # 视频（部分商品有）
            if i % 3 == 0:
                video = ProductVideo(
                    product_id=product.id,
                    filename=f'test_video_{i}.mp4',
                    filepath=f'uploads/videos/test_video_{i}.mp4',
                    duration=60
                )
                db.session.add(video)
            
            # 分析数据
            analytics = ProductAnalytics(
                product_id=product.id,
                view_count=i * 10,
                click_count=i * 5,
                video_play_count=i * 2 if i % 3 == 0 else 0
            )
            db.session.add(analytics)
        
        db.session.commit()
        print('测试数据添加完成！')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
