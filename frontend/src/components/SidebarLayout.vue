<script setup>
import { useRoute } from 'vue-router'
import '../styles/teacher.css'

defineProps({
  label: { type: String, required: true },
  links: { type: Array, required: true },
})

const route = useRoute()
</script>

<template>
  <div class="teacher-shell">
    <nav class="teacher-sidebar" :aria-label="label">
      <RouterLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        :class="{ active: route.path.startsWith(link.to) }"
      >
        {{ link.label }}
      </RouterLink>
    </nav>
    <div class="teacher-main">
      <RouterView :key="route.fullPath" />
    </div>
  </div>
</template>
