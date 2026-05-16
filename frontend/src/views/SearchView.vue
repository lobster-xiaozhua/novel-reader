<template>
  <div class="page-container">
    <h1 class="page-title">🔍 搜索</h1>

    <div class="search-box">
      <input
        v-model="query"
        class="input search-input"
        placeholder="搜索小说标题、作者..."
        @input="handleInput"
        @keyup.enter="doSearch"
      />
      <button class="btn btn-primary" @click="doSearch">搜索</button>
    </div>

    <div v-if="suggestions.length && query.length >= 2 && !hasSearched" class="suggestions">
      <div
        v-for="s in suggestions"
        :key="s.id || s.title"
        class="suggestion-item"
        @click="selectSuggestion(s)"
      >
        <span class="suggestion-title">{{ s.title }}</span>
        <span class="suggestion-author" v-if="s.author">{{ s.author }}</span>
      </div>
    </div>

    <div v-if="searching" class="loading-spinner">搜索中...</div>

    <div v-else-if="hasSearched">
      <div v-if="results.length" class="results-list">
        <p class="results-count">找到 {{ results.length }} 个结果</p>
        <BookCard
          v-for="book in results"
          :key="book.id"
          :book="book"
          @click="goToBook(book.id)"
        />
      </div>
      <div v-else class="empty-state">
        <div class="empty-icon">🔍</div>
        <div class="empty-text">没有找到相关书籍</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import BookCard from '../components/BookCard.vue'

const route = useRoute()
const router = useRouter()

const query = ref('')
const results = ref([])
const suggestions = ref([])
const searching = ref(false)
const hasSearched = ref(false)

let suggestTimer = null

onMounted(() => {
  if (route.query.q) {
    query.value = route.query.q
    doSearch()
  }
})

function handleInput() {
  hasSearched.value = false
  clearTimeout(suggestTimer)
  if (query.value.length < 2) {
    suggestions.value = []
    return
  }
  suggestTimer = setTimeout(async () => {
    try {
      const { data } = await api.get('/api/search/suggestions', { params: { q: query.value } })
      suggestions.value = data.items || data || []
    } catch (e) {
      suggestions.value = []
    }
  }, 300)
}

async function doSearch() {
  if (!query.value.trim()) return
  suggestions.value = []
  searching.value = true
  hasSearched.value = true
  try {
    const { data } = await api.get('/api/search', { params: { q: query.value } })
    results.value = data.items || data || []
  } catch (e) {
    results.value = []
  } finally {
    searching.value = false
  }
}

function selectSuggestion(item) {
  if (item.id) {
    goToBook(item.id)
  } else {
    query.value = item.title
    doSearch()
  }
}

function goToBook(id) {
  router.push(`/books/${id}`)
}
</script>

<style scoped>
.search-box {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.search-input {
  flex: 1;
}

.suggestions {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 24px;
}

.suggestion-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.suggestion-item:hover {
  background: var(--bg-hover);
}

.suggestion-item + .suggestion-item {
  border-top: 1px solid var(--border-color);
}

.suggestion-title {
  font-size: 14px;
  color: var(--text-primary);
}

.suggestion-author {
  font-size: 13px;
  color: var(--text-tertiary);
}

.results-count {
  font-size: 14px;
  color: var(--text-tertiary);
  margin-bottom: 16px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
