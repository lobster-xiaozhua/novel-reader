<template>
  <div class="page-container">
    <div v-if="loading" class="loading-spinner">加载中...</div>

    <template v-else-if="book">
      <div class="book-header">
        <div class="book-cover-large">
          <span class="cover-icon">📖</span>
        </div>
        <div class="book-meta-info">
          <h1 class="book-title">{{ book.title }}</h1>
          <p class="book-author" v-if="book.author">作者：{{ book.author }}</p>
          <p class="book-desc" v-if="book.description">{{ book.description }}</p>
          <div class="book-stats">
            <span v-if="book.chapter_count !== undefined">{{ book.chapter_count }} 章</span>
            <span v-if="book.word_count">{{ book.word_count }} 字</span>
          </div>
          <div class="book-actions">
            <button class="btn btn-primary" @click="startReading" v-if="chapters.length">开始阅读</button>
            <button class="btn btn-secondary" @click="toggleFavorite">
              {{ isFavorited ? '⭐ 已收藏' : '☆ 收藏' }}
            </button>
            <button class="btn btn-danger" @click="handleDelete">删除</button>
          </div>
        </div>
      </div>

      <section class="chapters-section">
        <h2 class="section-title">章节目录</h2>
        <div v-if="chapters.length" class="chapters-list">
          <div
            v-for="chapter in chapters"
            :key="chapter.id"
            class="chapter-item"
            @click="goToChapter(chapter)"
          >
            <span class="chapter-number">第{{ chapter.chapter_number }}章</span>
            <span class="chapter-title">{{ chapter.title }}</span>
            <span class="chapter-words" v-if="chapter.word_count">{{ chapter.word_count }}字</span>
          </div>
        </div>
        <div v-else class="empty-state">
          <div class="empty-icon">📄</div>
          <div class="empty-text">暂无章节</div>
        </div>
      </section>
    </template>

    <div v-else class="empty-state">
      <div class="empty-icon">😕</div>
      <div class="empty-text">未找到该书籍</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()

const book = ref(null)
const chapters = ref([])
const loading = ref(true)
const isFavorited = ref(false)

onMounted(async () => {
  const bookId = route.params.id
  try {
    const [bookRes, chaptersRes] = await Promise.all([
      api.get(`/api/books/${bookId}`),
      api.get(`/api/books/${bookId}/chapters`)
    ])
    book.value = bookRes.data
    chapters.value = chaptersRes.data.items || chaptersRes.data || []
  } catch (e) {
    // ignore
  } finally {
    loading.value = false
  }

  try {
    const { data } = await api.get('/api/favorites')
    const favList = data.items || data || []
    isFavorited.value = favList.some(f => f.book_id === Number(bookId) || f.book?.id === Number(bookId))
  } catch (e) {
    // ignore
  }
})

function startReading() {
  if (chapters.value.length) {
    const first = chapters.value[0]
    router.push(`/reader/${book.value.id}/${first.id}`)
  }
}

function goToChapter(chapter) {
  router.push(`/reader/${book.value.id}/${chapter.id}`)
}

async function toggleFavorite() {
  try {
    if (isFavorited.value) {
      isFavorited.value = false
    } else {
      await api.post('/api/favorites', { book_id: book.value.id })
      isFavorited.value = true
    }
  } catch (e) {
    alert('操作失败：' + (e.response?.data?.detail || e.message))
  }
}

async function handleDelete() {
  if (!confirm('确定要删除这本书吗？')) return
  try {
    await api.delete(`/api/books/${book.value.id}`)
    router.push('/books')
  } catch (e) {
    alert('删除失败：' + (e.response?.data?.detail || e.message))
  }
}
</script>

<style scoped>
.book-header {
  display: flex;
  gap: 32px;
  margin-bottom: 40px;
  padding: 32px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
}

.book-cover-large {
  flex-shrink: 0;
  width: 160px;
  height: 220px;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-icon {
  font-size: 48px;
  opacity: 0.6;
}

.book-meta-info {
  flex: 1;
  min-width: 0;
}

.book-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.book-author {
  font-size: 15px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.book-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.8;
  margin-bottom: 16px;
}

.book-stats {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--accent);
  margin-bottom: 20px;
}

.book-actions {
  display: flex;
  gap: 12px;
}

.chapters-section {
  margin-top: 8px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.chapters-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 8px;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: var(--text-secondary);
}

.chapter-item:hover {
  border-color: var(--accent);
  color: var(--text-primary);
}

.chapter-number {
  color: var(--accent);
  font-weight: 500;
  white-space: nowrap;
}

.chapter-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chapter-words {
  font-size: 12px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

@media (max-width: 768px) {
  .book-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  .book-actions {
    justify-content: center;
  }
}
</style>
