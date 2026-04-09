/**
 * 侧边栏待处理消息角标
 * 管理员在“系统设置”链接旁显示待处理密码重置申请数量
 */
(function () {
    const API_BASE = 'http://localhost:5001/api';

    function isAdmin() {
        try {
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            const roles = user.roles || [];
            return roles.some((role) => role.code === 'admin');
        } catch (e) {
            return false;
        }
    }

    async function loadPendingCount() {
        if (!isAdmin()) return;
        const token = localStorage.getItem('token');
        if (!token) return;

        try {
            const res = await fetch(`${API_BASE}/settings/reset_requests/pending_count`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await res.json();
            if (data.code === 0 && data.data.count > 0) {
                renderBadge(data.data.count);
            }
        } catch (e) {
        }
    }

    function renderBadge(count) {
        const links = document.querySelectorAll('a[href="settings.html"]');
        links.forEach((link) => {
            if (link.querySelector('.pending-badge')) return;
            link.style.position = 'relative';

            const badge = document.createElement('span');
            badge.className = 'pending-badge';
            badge.textContent = count > 99 ? '99+' : String(count);
            badge.style.cssText = 'position:absolute;top:6px;right:10px;min-width:16px;height:16px;display:flex;align-items:center;justify-content:center;background:#ef4444;color:#fff;font-size:10px;font-weight:700;border-radius:99px;padding:0 4px;';
            link.appendChild(badge);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            setTimeout(loadPendingCount, 500);
        });
    } else {
        setTimeout(loadPendingCount, 500);
    }
})();
