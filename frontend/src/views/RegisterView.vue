<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-header">
        <span class="register-icon">📖</span>
        <h1 class="register-title">创建账号</h1>
        <p class="register-subtitle">注册小说阅读器</p>
      </div>

      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label class="form-label">用户名 *</label>
          <input
            v-model="form.username"
            class="input"
            type="text"
            placeholder="请输入用户名"
            required
          />
        </div>
        <div class="form-group">
          <label class="form-label">邮箱</label>
          <input
            v-model="form.email"
            class="input"
            type="email"
            placeholder="请输入邮箱（可选）"
          />
        </div>
        <div class="form-group">
          <label class="form-label">密码 *</label>
          <input
            v-model="form.password"
            class="input"
            type="password"
            placeholder="请输入密码"
            required
          />
        </div>
        <div class="form-group">
          <label class="form-label">确认密码 *</label>
          <input
            v-model="form.confirmPassword"
            class="input"
            type="password"
            placeholder="请再次输入密码"
            required
          />
        </div>
        <div v-if="error" class="error-msg">{{ error }}</div>
        <div v-if="success" class="success-msg">{{ success }}</div>
        <button type="submit" class="btn btn-primary btn-full" :disabled="submitting">
          {{ submitting ? '注册中...' : '注册' }}
        </button>
      </form>

      <div class="register-footer">
        已有账号？
        <router-link to="/login">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = ref({ username: '', email: '', password: '', confirmPassword: '' })
const error = ref('')
const success = ref('')
const submitting = ref(false)

async function handleRegister() {
  error.value = ''
  success.value = ''

  if (form.value.password !== form.value.confirmPassword) {
    error.value = '两次输入的密码不一致'
    return
  }

  if (form.value.password.length < 6) {
    error.value = '密码长度至少6位'
    return
  }

  submitting.value = true
  try {
    await userStore.register({
      username: form.value.username,
      password: form.value.password,
      email: form.value.email || undefined
    })
    success.value = '注册成功，正在跳转到登录页...'
    setTimeout(() => {
      router.push('/login')
    }, 1500)
  } catch (e) {
    error.value = e.response?.data?.detail || '注册失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--bg-primary);
}

.register-card {
  width: 100%;
  max-width: 400px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 40px 32px;
}

.register-header {
  text-align: center;
  margin-bottom: 32px;
}

.register-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.register-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.register-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.error-msg {
  font-size: 13px;
  color: var(--danger);
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 6px;
}

.success-msg {
  font-size: 13px;
  color: var(--success);
  padding: 8px 12px;
  background: rgba(34, 197, 94, 0.1);
  border-radius: 6px;
}

.btn-full {
  width: 100%;
  padding: 12px;
  font-size: 15px;
  margin-top: 8px;
}

.register-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: var(--text-tertiary);
}

.register-footer a {
  color: var(--accent);
  font-weight: 500;
}
</style>
