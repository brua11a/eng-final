<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import CatalogueSearchBlock from '../../components/catalogue/CatalogueSearchBlock.vue'

const router = useRouter()

const teacherQ = ref('')
const unitQ = ref('')
const subjectName = ref('')
const subjectCode = ref('')
const studyQ = ref('')

function pushResults(name, query) {
  router.push({ name, query })
}

function searchPeople() {
  const name = teacherQ.value.trim()
  pushResults('catalogue-teachers-results', name ? { name } : {})
}

function searchUnits() {
  const name = unitQ.value.trim()
  pushResults('catalogue-units-results', name ? { name } : {})
}

function searchSubjects() {
  const name = subjectName.value.trim()
  const code = subjectCode.value.trim()
  const query = {}
  if (name) query.name = name
  if (code) query.code = code
  pushResults('catalogue-subjects-results', query)
}

function searchStudies() {
  const name = studyQ.value.trim()
  pushResults('catalogue-curricula-results', name ? { name } : {})
}
</script>

<template>
  <div>
    <h1 class="catalogue-page-title">Catalogue</h1>

    <CatalogueSearchBlock title="Search people" @search="searchPeople">
      <input v-model="teacherQ" type="search" placeholder="Staff name" />
    </CatalogueSearchBlock>

    <CatalogueSearchBlock title="Search units" @search="searchUnits">
      <input v-model="unitQ" type="search" placeholder="Unit name or code" />
    </CatalogueSearchBlock>

    <CatalogueSearchBlock title="Search subjects" horizontal-fields @search="searchSubjects">
      <input v-model="subjectName" type="search" placeholder="Subject name" />
      <input v-model="subjectCode" type="search" placeholder="Subject code" />
    </CatalogueSearchBlock>

    <CatalogueSearchBlock title="Search programmes" @search="searchStudies">
      <input v-model="studyQ" type="search" placeholder="Programme name" />
    </CatalogueSearchBlock>
  </div>
</template>
