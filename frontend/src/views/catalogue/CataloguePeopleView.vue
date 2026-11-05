<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import CatalogueSearchBlock from '../../components/catalogue/CatalogueSearchBlock.vue'

const router = useRouter()
const teacherQ = ref('')

function search() {
  const name = teacherQ.value.trim()
  router.push({ name: 'catalogue-teachers-results', query: name ? { name } : {} })
}
</script>

<template>
  <div>
    <h1 class="catalogue-page-title">People</h1>
    <CatalogueSearchBlock title="Search people" @search="search">
      <input v-model="teacherQ" type="search" placeholder="Staff name" />
    </CatalogueSearchBlock>
  </div>
</template>
