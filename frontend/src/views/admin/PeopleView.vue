<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import { useAdminReferenceData } from '../../composables/useAdminReferenceData'
import ApiMessages from '../../components/ApiMessages.vue'

const { faculties, programmes, facultyLabel, programmeLabel, error: refsError } = useAdminReferenceData()

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
  joined: new Date().toISOString().slice(0, 10),
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
      joined: `${s.value.joined}T00:00:00`,
      photo: s.value.photo || null,
    }),
  )
}
</script>

<template>
  <div>
    <h1 class="teacher-page-title">People</h1>
    <ApiMessages v-if="refsError" :error="refsError" />

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">New teacher</h2>
      <form class="admin-form" @submit.prevent="createTeacher">
        <label>Name <input v-model="t.name" required /></label>
        <label>Surname <input v-model="t.surname" required /></label>
        <label>Phone <input v-model="t.phone" required /></label>
        <label>Degree <input v-model="t.degree" required /></label>
        <label>Photo URL <input v-model="t.photo" /></label>
        <label>Working since <input v-model="t.working_since" type="date" required /></label>
        <label>
          Faculty
          <select v-model="t.faculty_id" required>
            <option value="" disabled>Select faculty</option>
            <option v-for="f in faculties" :key="f.id" :value="f.id">
              {{ facultyLabel(f) }}
            </option>
          </select>
        </label>
        <button type="submit" class="teacher-btn-save" :disabled="teacherApi.loading">Create</button>
      </form>
      <ApiMessages :error="teacherApi.error" :api-message="teacherApi.apiMessage" />
      <p v-if="teacherApi.result?.idx && !teacherApi.apiMessage" class="admin-ok">
        Created teacher {{ teacherApi.result.idx }}
      </p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">New student</h2>
      <form class="admin-form" @submit.prevent="createStudent">
        <label>Name <input v-model="s.name" required /></label>
        <label>Surname <input v-model="s.surname" required /></label>
        <label>Phone <input v-model="s.phone" required /></label>
        <label>Photo URL <input v-model="s.photo" /></label>
        <label>Joined <input v-model="s.joined" type="date" required /></label>
        <label>
          Programme
          <select v-model="s.programme" required>
            <option value="" disabled>Select programme</option>
            <option v-for="p in programmes" :key="p.id" :value="p.id">
              {{ programmeLabel(p) }}
            </option>
          </select>
        </label>
        <button type="submit" class="teacher-btn-save" :disabled="studentApi.loading">Create</button>
      </form>
      <ApiMessages :error="studentApi.error" :api-message="studentApi.apiMessage" />
      <p v-if="studentApi.result?.idx && !studentApi.apiMessage" class="admin-ok">
        Created student {{ studentApi.result.idx }}
      </p>
    </section>
  </div>
</template>
