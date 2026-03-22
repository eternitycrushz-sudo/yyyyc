/**
 * 全局工具函数
 */

// 全局图表数据加载函数（通用接口）
window.loadChartData = async function(productId) {
    if (!productId) {
        console.warn('loadChartData: productId is required')
        return
    }

    // 如果在goods_detail.html中，则使用该页面的具体实现
    // 该文件会覆盖这个全局函数
    if (typeof window._loadChartDataImpl === 'function') {
        return window._loadChartDataImpl(productId)
    }

    console.log('loadChartData called with productId:', productId)
}

/**
 * Toast 通知辅助函数（如果Toast.js未加载）
 */
if (typeof window.Toast === 'undefined') {
    window.Toast = {
        success: (message) => console.log('✓', message),
        error: (message) => console.error('✗', message),
        info: (message) => console.info('ℹ', message),
        warning: (message) => console.warn('⚠', message)
    }
}
