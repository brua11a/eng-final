<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import CatalogueSearchBlock from '../../components/catalogue/CatalogueSearchBlock.vue'

const router = useRouter()
const studyQ = ref('')

function searchPrograms() {
  const name = studyQ.value.trim()
  router.push({ name: 'catalogue-curricula-results', query: name ? { name } : {} })
}

function showAll() {
  router.push({ name: 'catalogue-curricula-results' })
}
</script>

<template>
  <div>
    <h1 class="catalogue-page-title">Programmes</h1>

    <CatalogueSearchBlock title="Search programmes" @search="searchPrograms">
      <input v-model="studyQ" type="search" placeholder="Programme name" />
    </CatalogueSearchBlock>

    <p class="catalogue-footer-link">
      <button type="button" class="catalogue-link-button" @click="showAll">Show all programmes</button>
    </p>
  </div>
</template>

<style scoped>
.catalogue-link-button {
  background: none;
  border: none;
  padding: 0;
  color: var(--cat-orange, #e8641b);
  font-size: 0.85rem;
  cursor: pointer;
  text-decoration: none;
}
.catalogue-link-button:hover {
  text-decoration: underline;
}
</style>
