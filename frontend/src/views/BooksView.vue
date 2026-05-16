<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">📚 书架</h1>
      <button class="btn btn-primary" @click="showAddBook = true">+ 添加书籍</button>
    </div>

    <div class="search-bar">
      <input
        v-model="searchQuery"
        class="input"
        placeholder="搜索书架中的书籍..."
        @input="handleSearch"
      />
    </div>

    <div v-if="booksStore.loading" class="loading-spinner">加载中...</div>

    <div v-else-if="booksStore.books.length" class="books-grid">
      <BookCard
        v-for="book in booksStore.books"
        :key="book.id"
        :book="book"
        @click="goToBook(book.id)"
      />
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">📚</div>
      <div class="empty-text">书架还是空的，添加一本书吧</div>
    </div>

    <div v-if="booksStore.total > booksStore.pageSize" class="pagination">
      <button :disabled="booksStore.currentPage <= 1" @click="changePage(booksStore.currentPage - 1)">上一页</button>
      <span class="page-info">{{ booksStore.currentPage }} / {{ totalPages }}</span>
      <button :disabled="booksStore.currentPage >= totalPages" @click="changePage(booksStore.currentPage + 1)">下一页</button>
    </div>

    <div v-if="showAddBook" class="modal-overlay" @click.self="showAddBook = false">
      <div class="modal">
        <h2 class="modal-title">添加书籍</h2>
        <div class="form-group">
          <label class="form-label">书名 *</label>
          <input v-model="newBook.title" class="input" placeholder="输入书名" />
        </div>
        <div class="form-group">
          <label class="form-label">作者</label>
          <input v-model="newBook.author" class="input" placeholder="输入作者" />
        </div>
        <div class="form-group">
          <label class="form-label">简介</label>
          <textarea v-model="newBook.description" class="input" rows="3" placeholder="输入简介"></textarea>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddBook = false">取消</button>
          <button class="btn btn-primary" @click="handleAddBook">添加</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useBooksStore } from '../stores/books'
import BookCard from '../components/BookCard.vue'

const router = useRouter()
const booksStore = useBooksStore()

const searchQuery = ref('')
const showAddBook = ref(false)
const newBook = ref({ title: '', author: '', description: '' })

const totalPages = computed(() => Math.ceil(booksStore.total / booksStore.pageSize))

onMounted(() => {
  booksStore.fetchBooks(1)
})

let searchTimer = null
function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (searchQuery.value.trim()) {
      router.push({ name: 'search', query: { q: searchQuery.value } })
    }
  }, 500)
}

function changePage(page) {
  booksStore.fetchBooks(page)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function goToBook(id) {
  router.push(`/books/${id}`)
}

async function handleAddBook() {
  if (!newBook.value.title.trim()) return
  try {
    await booksStore.createBook(newBook.value)
    showAddBook.value = false
    newBook.value = { title: '', author: '', description: '' }
    booksStore.fetchBooks(1)
  } catch (e) {
    alert('添加失败：' + (e.response?.data?.detail || e.message))
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header .page-title {
  margin-bottom: 0;
}

.search-bar {
  margin-bottom: 24px;
}

.books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 32px;
  width: 90%;
  max-width: 480px;
}

.modal-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

textarea.input {
  resize: vertical;
  min-height: 80px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}
</style>
