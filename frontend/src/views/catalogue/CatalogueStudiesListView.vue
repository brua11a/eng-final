<script setup>
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'

const api = useApiCall()

onMounted(() => api.run(() => catalogue.curricula('')))
</script>

<template>
  <div>
    <h1 class="catalogue-page-title">Lista kierunków studiów</h1>
    <p class="catalogue-hint">
      <RouterLink to="/catalogue/studia">← wróć do studiów</RouterLink>
    </p>
    <ApiMessages :error="api.error" :api-message="api.apiMessage" />
    <ul v-if="api.result?.curricula?.length" class="result-list">
      <li v-for="c in api.result.curricula" :key="c.id">
        <RouterLink
          :to="{ name: 'catalogue-curricula-results', query: { name: c.name } }"
        >
          {{ c.name }}
        </RouterLink>
        <span class="meta">rok {{ c.intake_year }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.result-list {
  list-style: none;
  padding: 0;
  margin: 0;
  background: #fff;
  border: 1px solid #c5cdd6;
}
.result-list li {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e8ecf0;
}
.result-list a {
  color: #e8641b;
}
.meta {
  display: block;
  font-size: 0.8rem;
  color: #5c6570;
}
</style>
