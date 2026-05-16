<template>
  <div class="book-card" @click="$emit('click')">
    <div class="book-cover">
      <div class="cover-placeholder">
        <span class="cover-icon">📖</span>
      </div>
    </div>
    <div class="book-info">
      <h3 class="book-title">{{ book.title }}</h3>
      <p class="book-author" v-if="book.author">{{ book.author }}</p>
      <p class="book-desc" v-if="book.description">{{ truncatedDesc }}</p>
      <div class="book-meta" v-if="book.chapter_count !== undefined">
        <span>{{ book.chapter_count }} 章</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  book: {
    type: Object,
    required: true
  }
})

defineEmits(['click'])

const truncatedDesc = computed(() => {
  if (!props.book.description) return ''
  return props.book.description.length > 80
    ? props.book.description.slice(0, 80) + '...'
    : props.book.description
})
</script>

<style scoped>
.book-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  gap: 16px;
  padding: 16px;
}

.book-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.book-cover {
  flex-shrink: 0;
  width: 80px;
  height: 110px;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-icon {
  font-size: 28px;
  opacity: 0.6;
}

.book-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.book-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.book-author {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
}

.book-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.book-meta {
  margin-top: auto;
  font-size: 12px;
  color: var(--accent);
}
</style>
