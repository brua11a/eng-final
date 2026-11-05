<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import CatalogueSearchBlock from '../../components/catalogue/CatalogueSearchBlock.vue'

const router = useRouter()
const unitQ = ref('')

function search() {
  const name = unitQ.value.trim()
  router.push({ name: 'catalogue-units-results', query: name ? { name } : {} })
}
</script>

<template>
  <div>
    <h1 class="catalogue-page-title">Organizational units</h1>
    <CatalogueSearchBlock title="Search units" @search="search">
      <input v-model="unitQ" type="search" placeholder="Unit name or code" />
    </CatalogueSearchBlock>
  </div>
</template>
