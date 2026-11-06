<script setup>
import { ref } from 'vue'
import { catalogue } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const teacherName = ref('')
const subjectName = ref('')
const subjectCode = ref('')
const curriculumName = ref('')
const subjectDetailCode = ref('')
const subjectGroupsCode = ref('')
const groupId = ref('')
const teacherIdx = ref('')

const teachersApi = useApiCall()
const subjectsApi = useApiCall()
const curriculaApi = useApiCall()
const subjectDetailApi = useApiCall()
const subjectGroupsApi = useApiCall()
const groupDetailApi = useApiCall()
const teacherDetailApi = useApiCall()
</script>

<template>
  <div class="page">
    <h1>Catalogue</h1>

    <section class="block">
      <h2>Teachers (GET /teachers)</h2>
      <form
        class="row"
        @submit.prevent="teachersApi.run(() => catalogue.teachers(teacherName))"
      >
        <input v-model="teacherName" placeholder="name filter" />
        <button type="submit" :disabled="teachersApi.loading">Search</button>
      </form>
      <ApiMessages :error="teachersApi.error" :api-message="teachersApi.apiMessage" />
      <JsonPreview :data="teachersApi.result" />
    </section>

    <section class="block">
      <h2>Subjects (GET /subjects)</h2>
      <form
        class="row"
        @submit.prevent="subjectsApi.run(() => catalogue.subjects(subjectName, subjectCode))"
      >
        <input v-model="subjectName" placeholder="name" />
        <input v-model="subjectCode" placeholder="code" />
        <button type="submit" :disabled="subjectsApi.loading">Search</button>
      </form>
      <ApiMessages :error="subjectsApi.error" :api-message="subjectsApi.apiMessage" />
      <JsonPreview :data="subjectsApi.result" />
    </section>

    <section class="block">
      <h2>Curricula (GET /curricula)</h2>
      <form
        class="row"
        @submit.prevent="curriculaApi.run(() => catalogue.curricula(curriculumName))"
      >
        <input v-model="curriculumName" placeholder="programme name" />
        <button type="submit" :disabled="curriculaApi.loading">Search</button>
      </form>
      <ApiMessages :error="curriculaApi.error" :api-message="curriculaApi.apiMessage" />
      <JsonPreview :data="curriculaApi.result" />
    </section>

    <section class="block">
      <h2>Subject detail (POST /subjects/detail)</h2>
      <form
        class="row"
        @submit.prevent="subjectDetailApi.run(() => catalogue.subjectDetail(subjectDetailCode))"
      >
        <input v-model="subjectDetailCode" placeholder="code" required />
        <button type="submit" :disabled="subjectDetailApi.loading">Load</button>
      </form>
      <ApiMessages
        :error="subjectDetailApi.error"
        :api-message="subjectDetailApi.apiMessage"
      />
      <JsonPreview :data="subjectDetailApi.result" />
    </section>

    <section class="block">
      <h2>Subject groups (POST /subjects/groups)</h2>
      <form
        class="row"
        @submit.prevent="subjectGroupsApi.run(() => catalogue.subjectGroups(subjectGroupsCode))"
      >
        <input v-model="subjectGroupsCode" placeholder="code" required />
        <button type="submit" :disabled="subjectGroupsApi.loading">Load</button>
      </form>
      <ApiMessages
        :error="subjectGroupsApi.error"
        :api-message="subjectGroupsApi.apiMessage"
      />
      <JsonPreview :data="subjectGroupsApi.result" />
    </section>

    <section class="block">
      <h2>Group detail (POST /groups/detail)</h2>
      <form
        class="row"
        @submit.prevent="groupDetailApi.run(() => catalogue.groupDetail(groupId))"
      >
        <input v-model="groupId" placeholder="group_id (UUID)" required />
        <button type="submit" :disabled="groupDetailApi.loading">Load</button>
      </form>
      <ApiMessages
        :error="groupDetailApi.error"
        :api-message="groupDetailApi.apiMessage"
      />
      <JsonPreview :data="groupDetailApi.result" />
    </section>

    <section class="block">
      <h2>Teacher detail (POST /teachers/detail)</h2>
      <form
        class="row"
        @submit.prevent="teacherDetailApi.run(() => catalogue.teacherDetail(teacherIdx))"
      >
        <input v-model="teacherIdx" placeholder="idx" required />
        <button type="submit" :disabled="teacherDetailApi.loading">Load</button>
      </form>
      <ApiMessages
        :error="teacherDetailApi.error"
        :api-message="teacherDetailApi.apiMessage"
      />
      <JsonPreview :data="teacherDetailApi.result" />
    </section>
  </div>
</template>

<style scoped>
.page h1 {
  margin-top: 0;
}
.block {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e5e7eb;
}
.block h2 {
  font-size: 1rem;
  margin-bottom: 0.5rem;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
input {
  padding: 0.4rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  min-width: 8rem;
}
button {
  padding: 0.4rem 0.75rem;
  background: #374151;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>
