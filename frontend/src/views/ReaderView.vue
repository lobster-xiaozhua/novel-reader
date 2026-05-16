<template>
  <div class="reader-view">
    <div class="reader-toolbar">
      <button class="toolbar-btn" @click="goBack" title="返回">← 返回</button>
      <span class="toolbar-title">{{ chapter?.title || '加载中...' }}</span>
      <div class="toolbar-right">
        <button class="toolbar-btn" @click="decreaseFontSize" title="缩小字体">A-</button>
        <span class="font-size-display">{{ fontSize }}px</span>
        <button class="toolbar-btn" @click="increaseFontSize" title="放大字体">A+</button>
      </div>
    </div>

    <div v-if="loading" class="loading-spinner">加载中...</div>

    <template v-else-if="chapter">
      <div class="reader-content" :style="{ fontSize: fontSize + 'px' }" ref="contentRef">
        <h1 class="chapter-title">{{ chapter.title }}</h1>
        <div class="chapter-body" v-html="formattedContent"></div>
      </div>

      <div class="reader-nav">
        <button
          class="nav-btn prev"
          :disabled="!hasPrev"
          @click="goPrev"
        >
          ← 上一章
        </button>
        <span class="nav-info">第{{ chapter.chapter_number }}章</span>
        <button
          class="nav-btn next"
          :disabled="!hasNext"
          @click="goNext"
        >
          下一章 →
        </button>
      </div>
    </template>

    <div v-else class="empty-state">
      <div class="empty-icon">😕</div>
      <div class="empty-text">章节内容加载失败</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()

const chapter = ref(null)
const chapters = ref([])
const loading = ref(true)
const fontSize = ref(parseInt(localStorage.getItem('reader-font-size') || '18'))
const contentRef = ref(null)
let saveTimer = null

const formattedContent = computed(() => {
  if (!chapter.value?.content) return ''
  return chapter.value.content
    .split('\n')
    .filter(p => p.trim())
    .map(p => `<p>${p}</p>`)
    .join('')
})

const currentIndex = computed(() => {
  if (!chapter.value || !chapters.value.length) return -1
  return chapters.value.findIndex(c => c.id === chapter.value.id)
})

const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value >= 0 && currentIndex.value < chapters.value.length - 1)

onMounted(async () => {
  await loadChapter()
  await loadChapters()
  await loadProgress()
})

onBeforeUnmount(() => {
  saveProgress()
  clearTimeout(saveTimer)
})

watch(() => route.params.chapterId, async (newId) => {
  if (newId) {
    await loadChapter()
    window.scrollTo({ top: 0 })
  }
})

watch(fontSize, (val) => {
  localStorage.setItem('reader-font-size', val.toString())
})

async function loadChapter() {
  loading.value = true
  try {
    const { data } = await api.get(`/api/chapters/${route.params.chapterId}`)
    chapter.value = data
    document.title = `${data.title} - 小说阅读器`
  } catch (e) {
    chapter.value = null
  } finally {
    loading.value = false
  }
}

async function loadChapters() {
  try {
    const { data } = await api.get(`/api/books/${route.params.bookId}/chapters`)
    chapters.value = data.items || data || []
  } catch (e) {
    // ignore
  }
}

async function loadProgress() {
  try {
    const { data } = await api.get(`/api/reading-progress/book/${route.params.bookId}`)
    if (data && data.chapter_number) {
      // If we're on the same chapter, restore scroll position
      if (chapter.value && data.chapter_number === chapter.value.chapter_number && data.scroll_position) {
        await nextTick()
        window.scrollTo({ top: data.scroll_position })
      }
    }
  } catch (e) {
    // ignore
  }
}

function saveProgress() {
  if (!chapter.value) return
  const scrollPosition = window.scrollY
  api.post(`/api/reading-progress/book/${route.params.bookId}`, {
    chapter_number: chapter.value.chapter_number,
    scroll_position: scrollPosition
  }).catch(() => {})
}

function scheduleSave() {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(saveProgress, 2000)
}

if (typeof window !== 'undefined') {
  window.addEventListener('scroll', scheduleSave)
  onBeforeUnmount(() => {
    window.removeEventListener('scroll', scheduleSave)
  })
}

function goBack() {
  router.push(`/books/${route.params.bookId}`)
}

function goPrev() {
  if (!hasPrev.value) return
  const prev = chapters.value[currentIndex.value - 1]
  router.push(`/reader/${route.params.bookId}/${prev.id}`)
}

function goNext() {
  if (!hasNext.value) return
  const next = chapters.value[currentIndex.value + 1]
  router.push(`/reader/${route.params.bookId}/${next.id}`)
}

function increaseFontSize() {
  if (fontSize.value < 28) fontSize.value += 2
}

function decreaseFontSize() {
  if (fontSize.value > 12) fontSize.value -= 2
}
</script>

<style scoped>
.reader-view {
  min-height: 100vh;
  background: var(--bg-primary);
}

.reader-toolbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  padding: 0 24px;
  z-index: 100;
  gap: 16px;
}

.toolbar-btn {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.toolbar-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.toolbar-title {
  flex: 1;
  font-size: 15px;
  color: var(--text-primary);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.font-size-display {
  font-size: 12px;
  color: var(--text-tertiary);
  min-width: 36px;
  text-align: center;
}

.reader-content {
  max-width: 720px;
  margin: 0 auto;
  padding: 80px 24px 120px;
  line-height: 1.9;
  color: var(--text-primary);
}

.chapter-title {
  font-family: 'Noto Serif SC', 'Source Han Serif SC', 'STSong', Georgia, serif;
  font-size: 1.6em;
  font-weight: 700;
  text-align: center;
  margin-bottom: 40px;
  color: var(--text-primary);
}

.chapter-body :deep(p) {
  font-family: 'Noto Serif SC', 'Source Han Serif SC', 'STSong', Georgia, serif;
  text-indent: 2em;
  margin-bottom: 1em;
  color: #cbd5e1;
  line-height: 1.9;
}

.reader-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  z-index: 100;
}

.nav-btn {
  padding: 10px 24px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.nav-info {
  font-size: 14px;
  color: var(--text-tertiary);
}
</style>
