#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = 'http://localhost:5000'

def test_api_endpoints():
    """测试API端点"""
    print("开始系统测试...")
    
    # 测试商品列表
    response = requests.get(f'{BASE_URL}/api/products')
    print(f"商品列表API: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"获取到 {len(data.get('products', []))} 个商品")
    
    # 测试分析数据
    response = requests.get(f'{BASE_URL}/api/analytics/dashboard')
    print(f"分析数据API: {response.status_code}")
    
    # 测试行为跟踪
    event_data = {
        'event_type': 'test_event',
        'event_data': {'test': True}
    }
    response = requests.post(f'{BASE_URL}/api/events', json=event_data)
    print(f"行为跟踪API: {response.status_code}")
    
    print("系统测试完成！")

if __name__ == '__main__':
    test_api_endpoints()
