import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './api/client'
import { useAuthStore } from './stores/auth'
import './style.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

setUnauthorizedHandler(() => {
  useAuthStore().logout()
  router.push({ name: 'login' })
})

app.use(router)
app.mount('#app')
