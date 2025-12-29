/**
 * Toast 通知组件
 * 
 * 特性：
 * - 从右侧滑入到中间
 * - 带进度条自动消失
 * - 支持多个堆叠显示
 * - 超过3个自动移除最早的
 * 
 * 使用方式：
 * Toast.success('操作成功')
 * Toast.error('操作失败')
 * Toast.info('提示信息')
 * Toast.warning('警告信息')
 */

const Toast = {
    container: null,
    toasts: [],
    maxCount: 3,
    duration: 3000, // 默认3秒
    
    // 初始化容器
    init() {
        if (this.container) return
        
        this.container = document.createElement('div')
        this.container.id = 'toast-container'
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            pointer-events: none;
        `
        document.body.appendChild(this.container)
        
        // 注入样式
        const style = document.createElement('style')
        style.textContent = `
            .toast-item {
                min-width: 300px;
                max-width: 500px;
                padding: 16px 20px;
                border-radius: 12px;
                backdrop-filter: blur(10px);
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                pointer-events: auto;
                position: relative;
                overflow: hidden;
                transform: translateX(100vw);
                opacity: 0;
                animation: toast-slide-in 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            }
            
            .toast-item.removing {
                animation: toast-slide-out 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
                overflow: hidden;
            }
            
            @keyframes toast-slide-in {
                from {
                    transform: translateX(100vw);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes toast-slide-out {
                from {
                    transform: translateY(0);
                    opacity: 1;
                    max-height: 100px;
                    margin-bottom: 10px;
                    padding: 16px 20px;
                }
                to {
                    transform: translateY(-20px);
                    opacity: 0;
                    max-height: 0;
                    margin-bottom: 0;
                    padding: 0 20px;
                }
            }
            
            .toast-success {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.95), rgba(5, 150, 105, 0.95));
                border: 1px solid rgba(16, 185, 129, 0.3);
            }
            
            .toast-error {
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.95), rgba(185, 28, 28, 0.95));
                border: 1px solid rgba(239, 68, 68, 0.3);
            }
            
            .toast-info {
                background: linear-gradient(135deg, rgba(19, 200, 236, 0.95), rgba(6, 182, 212, 0.95));
                border: 1px solid rgba(19, 200, 236, 0.3);
            }
            
            .toast-warning {
                background: linear-gradient(135deg, rgba(245, 158, 11, 0.95), rgba(217, 119, 6, 0.95));
                border: 1px solid rgba(245, 158, 11, 0.3);
            }
            
            .toast-content {
                display: flex;
                align-items: center;
                gap: 12px;
                color: white;
            }
            
            .toast-icon {
                font-size: 24px;
                flex-shrink: 0;
            }
            
            .toast-message {
                font-size: 14px;
                font-weight: 500;
                line-height: 1.5;
            }
            
            .toast-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: rgba(255,255,255,0.5);
                border-radius: 0 0 12px 12px;
                animation: toast-progress linear forwards;
            }
            
            @keyframes toast-progress {
                from { width: 100%; }
                to { width: 0%; }
            }
        `
        document.head.appendChild(style)
    },
    
    // 显示 Toast
    show(message, type = 'info', duration = this.duration) {
        this.init()
        
        // 超过最大数量，移除最早的
        while (this.toasts.length >= this.maxCount) {
            this.remove(this.toasts[0].id, true)
        }
        
        const id = Date.now() + Math.random()
        const icons = {
            success: 'check_circle',
            error: 'error',
            info: 'info',
            warning: 'warning'
        }
        
        const toast = document.createElement('div')
        toast.className = `toast-item toast-${type}`
        toast.innerHTML = `
            <div class="toast-content">
                <span class="material-symbols-outlined toast-icon">${icons[type]}</span>
                <span class="toast-message">${message}</span>
            </div>
            <div class="toast-progress" style="animation-duration: ${duration}ms"></div>
        `
        
        this.container.appendChild(toast)
        this.toasts.push({ id, element: toast })
        
        // 自动移除
        setTimeout(() => {
            this.remove(id)
        }, duration)
        
        return id
    },
    
    // 移除 Toast
    remove(id, immediate = false) {
        const index = this.toasts.findIndex(t => t.id === id)
        if (index === -1) return
        
        const { element } = this.toasts[index]
        
        if (immediate) {
            element.remove()
            this.toasts.splice(index, 1)
        } else {
            element.classList.add('removing')
            setTimeout(() => {
                element.remove()
                const idx = this.toasts.findIndex(t => t.id === id)
                if (idx !== -1) this.toasts.splice(idx, 1)
            }, 500)
        }
    },
    
    // 快捷方法
    success(message, duration) {
        return this.show(message, 'success', duration)
    },
    
    error(message, duration) {
        return this.show(message, 'error', duration)
    },
    
    info(message, duration) {
        return this.show(message, 'info', duration)
    },
    
    warning(message, duration) {
        return this.show(message, 'warning', duration)
    }
}

// 导出给 Vue 使用
if (typeof window !== 'undefined') {
    window.Toast = Toast
}
