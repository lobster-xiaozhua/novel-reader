function refreshTask(taskId) {
    fetch(`/crawler/${taskId}/`)
        .then(r => r.json())
        .then(data => {
            const card = document.querySelector(`[data-task-id="${taskId}"]`);
            if (card) {
                const statusEl = card.querySelector('.task-status');
                statusEl.className = `task-status status-${data.status}`;
                statusEl.textContent = getStatusText(data.status);
            }
        })
        .catch(() => {});
}

function getStatusText(status) {
    const map = {
        'pending': '等待中',
        'running': '运行中',
        'completed': '已完成',
        'failed': '失败',
        'cancelled': '已取消'
    };
    return map[status] || status;
}

// Auto-refresh running tasks
setInterval(() => {
    document.querySelectorAll('.task-status.status-running').forEach(el => {
        const card = el.closest('.task-card');
        if (card) {
            const taskId = card.dataset.taskId;
            refreshTask(taskId);
        }
    });
}, 5000);
