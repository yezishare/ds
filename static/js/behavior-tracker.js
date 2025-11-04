class BehaviorTracker {
    constructor() {
        this.sessionId = this.getSessionId();
        this.endpoint = '/api/events';
        this.queue = [];
        this.isSending = false;
        this.engagementStartTime = Date.now();
        this.lastActivityTime = Date.now();
        
        this.init();
    }
    
    init() {
        // 页面浏览事件
        this.trackPageView();
        
        // 用户活动跟踪
        this.trackUserActivity();
        
        // 定期发送队列中的事件
        setInterval(() => this.flushQueue(), 5000);
        
        // 页面卸载前发送剩余事件
        window.addEventListener('beforeunload', () => this.sendBeaconEvents());
    }
    
    getSessionId() {
        let sessionId = localStorage.getItem('session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('session_id', sessionId);
        }
        return sessionId;
    }
    
    track(eventType, productId = null, eventData = {}) {
        const event = {
            event_type: eventType,
            product_id: productId,
            event_data: {
                ...eventData,
                timestamp: new Date().toISOString(),
                url: window.location.href,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight
                }
            }
        };
        
        this.queue.push(event);
        this.updateActivityTime();
        
        // 重要事件立即发送
        if (['purchase', 'video_play', 'session_end'].includes(eventType)) {
            this.flushQueue();
        }
    }
    
    trackPageView() {
        this.track('page_view', null, {
            referrer: document.referrer,
            page_title: document.title,
            navigation_type: performance.getEntriesByType('navigation')[0]?.type
        });
    }
    
    trackUserActivity() {
        const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        activityEvents.forEach(eventType => {
            document.addEventListener(eventType, () => this.updateActivityTime(), { passive: true });
        });
        
        // 页面隐藏时计算停留时间
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.trackEngagementTime();
            }
        });
    }
    
    updateActivityTime() {
        this.lastActivityTime = Date.now();
    }
    
    trackEngagementTime() {
        const now = Date.now();
        const activeTime = Math.round((this.lastActivityTime - this.engagementStartTime) / 1000);
        const totalTime = Math.round((now - this.engagementStartTime) / 1000);
        
        if (activeTime > 0) {
            this.track('engagement_time', null, {
                active_time: activeTime,
                total_time: totalTime
            });
        }
        
        this.engagementStartTime = now;
        this.lastActivityTime = now;
    }
    
    async flushQueue() {
        if (this.isSending || this.queue.length === 0) return;
        
        this.isSending = true;
        const eventsToSend = [...this.queue];
        this.queue = [];
        
        try {
            for (const event of eventsToSend) {
                await this.sendEvent(event);
            }
        } catch (error) {
            console.error('Failed to send events:', error);
            // 重新加入队列（除了session_end事件）
            const retryEvents = eventsToSend.filter(e => e.event_type !== 'session_end');
            this.queue.unshift(...retryEvents);
        } finally {
            this.isSending = false;
        }
    }
    
    async sendEvent(event) {
        const response = await fetch(this.endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': this.sessionId
            },
            body: JSON.stringify(event)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return response.json();
    }
    
    sendBeaconEvents() {
        // 发送会话结束事件
        this.trackEngagementTime();
        
        const sessionEndEvent = {
            event_type: 'session_end',
            event_data: {
                timestamp: new Date().toISOString(),
                url: window.location.href
            }
        };
        
        // 使用sendBeacon发送重要事件
        const eventsToSend = this.queue.filter(e => 
            ['session_end', 'purchase', 'video_play'].includes(e.event_type)
        );
        
        eventsToSend.forEach(event => {
            const blob = new Blob([JSON.stringify(event)], { type: 'application/json' });
            navigator.sendBeacon(this.endpoint, blob);
        });
    }
}

// 初始化并暴露到全局
window.behaviorTracker = new BehaviorTracker();

// 页面卸载前确保发送数据
window.addEventListener('beforeunload', () => {
    window.behaviorTracker.sendBeaconEvents();
});
