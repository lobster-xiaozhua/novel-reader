import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useBooksStore = defineStore('books', () => {
  const books = ref([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(12)
  const loading = ref(false)
  const currentBook = ref(null)

  async function fetchBooks(page = 1, size = 12) {
    loading.value = true
    try {
      const { data } = await api.get('/api/books', {
        params: { page, page_size: size }
      })
      books.value = data.items
      total.value = data.total
      currentPage.value = data.page
      pageSize.value = data.page_size
    } finally {
      loading.value = false
    }
  }

  async function fetchBook(id) {
    loading.value = true
    try {
      const { data } = await api.get(`/api/books/${id}`)
      currentBook.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function createBook(bookData) {
    const { data } = await api.post('/api/books', bookData)
    return data
  }

  async function deleteBook(id) {
    await api.delete(`/api/books/${id}`)
    if (currentBook.value?.id === id) {
      currentBook.value = null
    }
  }

  return { books, total, currentPage, pageSize, loading, currentBook, fetchBooks, fetchBook, createBook, deleteBook }
})
