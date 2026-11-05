<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const tabs = computed(() => auth.visibleTabs)

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}

function isActive(tab) {
  return route.path.startsWith(tab.path)
}

const wideLayout = computed(() => route.path.startsWith('/catalogue'))
</script>

<template>
  <div class="layout">
    <header class="header">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true" />
        Politechnika — catalogue
      </div>
      <nav v-if="auth.isLoggedIn" class="tabs">
        <RouterLink
          v-for="t in tabs"
          :key="t.name"
          :to="t.path"
          class="tab"
          :class="{ active: isActive(t) }"
        >
          {{ t.label }}
        </RouterLink>
      </nav>
      <div v-if="auth.isLoggedIn" class="user">
        <span>{{ auth.email }}</span>
        <span class="idx">{{ auth.idx }}</span>
        <span v-for="r in auth.roles" :key="r" class="badge">{{ r }}</span>
        <button type="button" class="btn-link" @click="logout">Logout</button>
      </div>
    </header>
    <main class="main" :class="{ 'main--wide': wideLayout }">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}
.brand {
  font-weight: 600;
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.brand-mark {
  width: 2rem;
  height: 2rem;
  background: linear-gradient(135deg, #1a3352 50%, #e8641b 50%);
  border-radius: 2px;
  flex-shrink: 0;
}
.tabs {
  display: flex;
  gap: 0.5rem;
  flex: 1;
}
.tab {
  padding: 0.35rem 0.75rem;
  text-decoration: none;
  color: #374151;
  border-radius: 4px;
}
.tab.active,
.tab.router-link-active {
  background: #e8641b;
  color: #fff;
}
.user {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}
.idx {
  color: #6b7280;
}
.badge {
  background: #e5e7eb;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  font-size: 0.75rem;
}
.btn-link {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  text-decoration: underline;
}
.main {
  flex: 1;
  padding: 1rem;
  max-width: 960px;
  width: 100%;
  margin: 0 auto;
}
.main--wide {
  max-width: none;
  padding: 1rem 0 0;
}
</style>
