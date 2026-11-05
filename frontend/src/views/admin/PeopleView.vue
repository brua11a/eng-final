<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const teacherApi = useApiCall()
const studentApi = useApiCall()

const t = ref({
  name: '',
  surname: '',
  phone: '',
  degree: '',
  photo: '',
  working_since: '2020-01-01',
  faculty_id: '',
})

const s = ref({
  name: '',
  surname: '',
  phone: '',
  photo: '',
  joined: new Date().toISOString(),
  programme: '',
})

function createTeacher() {
  teacherApi.run(() =>
    admin.createTeacher({
      ...t.value,
      photo: t.value.photo || null,
    }),
  )
}

function createStudent() {
  studentApi.run(() =>
    admin.createStudent({
      ...s.value,
      photo: s.value.photo || null,
    }),
  )
}
</script>

<template>
  <div>
    <h1>Create people</h1>

    <section class="block">
      <h2>POST /admin/teachers</h2>
      <form class="form" @submit.prevent="createTeacher">
        <input v-for="(_, key) in t" :key="key" v-model="t[key]" :placeholder="key" />
        <button type="submit" :disabled="teacherApi.loading">Create teacher</button>
      </form>
      <ApiMessages :error="teacherApi.error" :api-message="teacherApi.apiMessage" />
      <JsonPreview :data="teacherApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/students</h2>
      <form class="form" @submit.prevent="createStudent">
        <input v-for="(_, key) in s" :key="key" v-model="s[key]" :placeholder="key" />
        <button type="submit" :disabled="studentApi.loading">Create student</button>
      </form>
      <ApiMessages :error="studentApi.error" :api-message="studentApi.apiMessage" />
      <JsonPreview :data="studentApi.result" />
    </section>
  </div>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 24rem;
}
.block {
  margin-bottom: 2rem;
}
</style>
