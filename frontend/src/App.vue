<template>
  <div class="app-layout">
    <NavBar v-if="showNav" />
    <main class="main-content" :class="{ 'no-nav': !showNav }">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'

const route = useRoute()

const showNav = computed(() => {
  return route.name !== 'reader' && route.name !== 'login' && route.name !== 'register'
})
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  background: var(--bg-primary);
}

.main-content {
  padding-top: 64px;
  min-height: 100vh;
}

.main-content.no-nav {
  padding-top: 0;
}
</style>
