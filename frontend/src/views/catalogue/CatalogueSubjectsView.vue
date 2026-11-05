<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import CatalogueSearchBlock from '../../components/catalogue/CatalogueSearchBlock.vue'

const router = useRouter()
const subjectName = ref('')
const subjectCode = ref('')

function search() {
  const name = subjectName.value.trim()
  const code = subjectCode.value.trim()
  const query = {}
  if (name) query.name = name
  if (code) query.code = code
  router.push({ name: 'catalogue-subjects-results', query })
}
</script>

<template>
  <div>
    <h1 class="catalogue-page-title">Subjects</h1>
    <CatalogueSearchBlock title="Search subjects" horizontal-fields @search="search">
      <input v-model="subjectName" type="search" placeholder="Subject name" />
      <input v-model="subjectCode" type="search" placeholder="Subject code" />
    </CatalogueSearchBlock>
  </div>
</template>
