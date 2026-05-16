<template>
  <div class="page-container">
    <h1 class="page-title">🏠 首页</h1>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">📚</div>
        <div class="stat-value">{{ stats.bookCount }}</div>
        <div class="stat-label">书籍总数</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📖</div>
        <div class="stat-value">{{ stats.readingCount }}</div>
        <div class="stat-label">阅读中</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">⭐</div>
        <div class="stat-value">{{ stats.favoriteCount }}</div>
        <div class="stat-label">收藏数</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-value">{{ stats.completedCount }}</div>
        <div class="stat-label">已读完</div>
      </div>
    </div>

    <section class="section">
      <div class="section-header">
        <h2 class="section-title">最近阅读</h2>
        <router-link to="/books" class="section-link">查看全部 →</router-link>
      </div>
      <div v-if="recentBooks.length" class="books-grid">
        <BookCard
          v-for="book in recentBooks"
          :key="book.id"
          :book="book"
          @click="goToBook(book.id)"
        />
      </div>
      <div v-else class="empty-state">
        <div class="empty-icon">📚</div>
        <div class="empty-text">还没有阅读记录，去书架看看吧</div>
      </div>
    </section>

    <section class="section">
      <div class="section-header">
        <h2 class="section-title">快速操作</h2>
      </div>
      <div class="quick-actions">
        <router-link to="/search" class="action-card">
          <span class="action-icon">🔍</span>
          <span class="action-text">搜索小说</span>
        </router-link>
        <router-link to="/crawler" class="action-card">
          <span class="action-icon">🕷️</span>
          <span class="action-text">爬取小说</span>
        </router-link>
        <router-link to="/books" class="action-card">
          <span class="action-icon">📚</span>
          <span class="action-text">浏览书架</span>
        </router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import BookCard from '../components/BookCard.vue'

const router = useRouter()

const stats = ref({
  bookCount: 0,
  readingCount: 0,
  favoriteCount: 0,
  completedCount: 0
})

const recentBooks = ref([])

onMounted(async () => {
  try {
    const { data } = await api.get('/api/books', { params: { page: 1, page_size: 6 } })
    recentBooks.value = data.items || []
    stats.value.bookCount = data.total || 0
  } catch (e) {
    // ignore
  }

  try {
    const { data } = await api.get('/api/favorites')
    stats.value.favoriteCount = data.length || data.items?.length || 0
  } catch (e) {
    // ignore
  }
})

function goToBook(id) {
  router.push(`/books/${id}`)
}
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 40px;
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  transition: all 0.3s;
}

.stat-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.stat-icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--accent);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-tertiary);
}

.section {
  margin-bottom: 40px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-link {
  font-size: 14px;
  color: var(--accent);
}

.books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  text-decoration: none;
  color: var(--text-primary);
  transition: all 0.3s;
}

.action-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
  color: var(--accent);
}

.action-icon {
  font-size: 36px;
}

.action-text {
  font-size: 15px;
  font-weight: 500;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>
