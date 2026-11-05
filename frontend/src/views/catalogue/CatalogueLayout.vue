<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import '../../styles/catalogue.css'

const route = useRoute()

const links = [
  { label: 'Home', to: '/catalogue', section: 'home' },
  { label: 'People', to: '/catalogue/osoby', section: 'people' },
  { label: 'Units', to: '/catalogue/jednostki', section: 'units' },
  { label: 'Subjects', to: '/catalogue/przedmioty', section: 'subjects' },
  { label: 'Programmes', to: '/catalogue/studia', section: 'studies' },
]

const wideMain = computed(
  () => route.path.includes('/wyniki') || route.name === 'catalogue-subject-detail',
)

function isActive(item) {
  const section = route.meta.catalogueSection
  if (item.section === 'home') {
    return route.path === '/catalogue' || route.path === '/catalogue/'
  }
  if (section) {
    return section === item.section
  }
  return route.path.startsWith(item.to)
}
</script>

<template>
  <div class="catalogue-shell" :class="{ 'catalogue-shell--wide-main': wideMain }">
    <nav class="catalogue-sidebar" aria-label="Catalogue">
      <div class="sidebar-section">Menu</div>
      <RouterLink
        v-for="item in links"
        :key="item.to"
        :to="item.to"
        :class="{ active: isActive(item) }"
      >
        {{ item.label }}
      </RouterLink>
    </nav>
    <div class="catalogue-main">
      <RouterView />
    </div>
  </div>
</template>
