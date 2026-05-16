<template>
  <div class="page-container">
    <h1 class="page-title">🕷️ 爬虫管理</h1>

    <div class="crawler-input">
      <input
        v-model="url"
        class="input"
        placeholder="输入小说页面URL..."
        @keyup.enter="createTask"
      />
      <button class="btn btn-primary" @click="createTask" :disabled="creating">
        {{ creating ? '创建中...' : '开始爬取' }}
      </button>
    </div>

    <section class="tasks-section">
      <h2 class="section-title">任务列表</h2>

      <div v-if="loadingTasks" class="loading-spinner">加载中...</div>

      <div v-else-if="tasks.length" class="tasks-list">
        <div v-for="task in tasks" :key="task.id" class="task-card">
          <div class="task-info">
            <div class="task-url">{{ task.url }}</div>
            <div class="task-meta">
              <span class="task-status" :class="statusClass(task.status)">
                {{ statusText(task.status) }}
              </span>
              <span class="task-time" v-if="task.created_at">{{ formatTime(task.created_at) }}</span>
            </div>
            <div class="task-detail" v-if="task.message">{{ task.message }}</div>
          </div>
          <button class="btn btn-secondary btn-sm" @click="refreshTask(task.id)">刷新</button>
        </div>
      </div>

      <div v-else class="empty-state">
        <div class="empty-icon">🕷️</div>
        <div class="empty-text">暂无爬虫任务</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const url = ref('')
const creating = ref(false)
const loadingTasks = ref(false)
const tasks = ref([])

onMounted(() => {
  loadTasks()
})

async function loadTasks() {
  loadingTasks.value = true
  try {
    const { data } = await api.get('/api/crawler/tasks')
    tasks.value = data.items || data || []
  } catch (e) {
    tasks.value = []
  } finally {
    loadingTasks.value = false
  }
}

async function createTask() {
  if (!url.value.trim()) return
  creating.value = true
  try {
    await api.post('/api/crawler/tasks', { url: url.value })
    url.value = ''
    await loadTasks()
  } catch (e) {
    alert('创建任务失败：' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

async function refreshTask(id) {
  try {
    const { data } = await api.get(`/api/crawler/tasks/${id}`)
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx !== -1) {
      tasks.value[idx] = data
    }
  } catch (e) {
    // ignore
  }
}

function statusClass(status) {
  const map = {
    pending: 'status-pending',
    running: 'status-running',
    completed: 'status-completed',
    failed: 'status-failed'
  }
  return map[status] || 'status-pending'
}

function statusText(status) {
  const map = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

function formatTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}
</script>

<style scoped>
.crawler-input {
  display: flex;
  gap: 12px;
  margin-bottom: 32px;
}

.crawler-input .input {
  flex: 1;
}

.tasks-section {
  margin-top: 8px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-url {
  font-size: 14px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 8px;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-status {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 20px;
  font-weight: 500;
}

.status-pending {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.status-running {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.status-completed {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.status-failed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.task-time {
  font-size: 12px;
  color: var(--text-tertiary);
}

.task-detail {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 6px;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 13px;
}
</style>
