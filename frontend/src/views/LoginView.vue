<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const err = ref('')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function submit() {
  err.value = ''
  loading.value = true
  try {
    const res = await auth.login(email.value, password.value)
    if (!res.ok) {
      err.value = res.err
      return
    }
    const redirect = route.query.redirect
    router.push(typeof redirect === 'string' ? redirect : auth.defaultRoute)
  } catch (e) {
    err.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <form class="card" @submit.prevent="submit">
      <h1>Login</h1>
      <label>
        Email
        <input v-model="email" type="email" required autocomplete="username" />
      </label>
      <label>
        Password
        <input v-model="password" type="password" required autocomplete="current-password" />
      </label>
      <p v-if="err" class="err">{{ err }}</p>
      <button type="submit" :disabled="loading">{{ loading ? '…' : 'Sign in' }}</button>
    </form>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
}
.card {
  background: #fff;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
}
input {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}
button {
  padding: 0.6rem;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.err {
  color: #9b1c1c;
  font-size: 0.9rem;
}
</style>
