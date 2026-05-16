<template>
  <nav class="navbar">
    <div class="nav-inner">
      <router-link to="/" class="nav-brand">
        <span class="brand-icon">📖</span>
        <span class="brand-text">小说阅读器</span>
      </router-link>
      <div class="nav-links">
        <router-link to="/" class="nav-link" :class="{ active: route.name === 'home' }">
          <span class="nav-icon">🏠</span>
          <span>首页</span>
        </router-link>
        <router-link to="/books" class="nav-link" :class="{ active: route.name === 'books' || route.name === 'book-detail' }">
          <span class="nav-icon">📚</span>
          <span>书架</span>
        </router-link>
        <router-link to="/search" class="nav-link" :class="{ active: route.name === 'search' }">
          <span class="nav-icon">🔍</span>
          <span>搜索</span>
        </router-link>
        <router-link to="/crawler" class="nav-link" :class="{ active: route.name === 'crawler' }">
          <span class="nav-icon">🕷️</span>
          <span>爬虫</span>
        </router-link>
      </div>
      <div class="nav-user">
        <template v-if="userStore.isLoggedIn">
          <span class="user-name">{{ userStore.username }}</span>
          <button class="btn-logout" @click="handleLogout">退出</button>
        </template>
        <template v-else>
          <router-link to="/login" class="btn-login">登录</router-link>
        </template>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

async function handleLogout() {
  await userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  z-index: 100;
  backdrop-filter: blur(12px);
}

.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 32px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
}

.brand-icon {
  font-size: 24px;
}

.nav-links {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  text-decoration: none;
  color: var(--text-secondary);
  font-size: 14px;
  transition: all 0.2s;
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.nav-link.active {
  color: var(--accent);
  background: rgba(245, 158, 11, 0.1);
}

.nav-icon {
  font-size: 16px;
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  color: var(--text-secondary);
  font-size: 14px;
}

.btn-logout {
  padding: 6px 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-logout:hover {
  border-color: #ef4444;
  color: #ef4444;
}

.btn-login {
  padding: 6px 20px;
  border-radius: 6px;
  background: var(--accent);
  color: #0f172a;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s;
}

.btn-login:hover {
  background: var(--accent-hover);
}
</style>
