<script setup>
import { onMounted, ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import { useAdminReferenceData } from '../../composables/useAdminReferenceData'
import ApiMessages from '../../components/ApiMessages.vue'

const {
  faculties,
  programmes,
  students,
  terms,
  facultyLabel,
  programmeLabel,
  error: refsError,
  load: reloadRefs,
} = useAdminReferenceData()

const teacherApi = useApiCall()
const studentApi = useApiCall()
const adminApi = useApiCall()
const enrolApi = useApiCall()

const a = ref({ idx: '', name: '', surname: '', phone: '' })
const enrol = ref({ student_idx: '', term_id: '' })

// Prefill idx fields with the next free numbers; the admin may change them.
async function suggestIdx() {
  try {
    const next = await admin.nextIdx()
    t.value.idx = next.teacher
    s.value.idx = next.student
    a.value.idx = next.admin
  } catch {
    // Leave the fields for manual input.
  }
}

onMounted(suggestIdx)

async function afterCreate(api) {
  if (api.result && !api.apiMessage && !api.error) {
    reloadRefs()
    await suggestIdx()
  }
}

async function createAdmin() {
  await adminApi.run(() => admin.createAdmin(a.value))
  await afterCreate(adminApi)
}

function enrolStudent() {
  enrolApi.run(() => admin.enrolStudent(enrol.value))
}

const t = ref({
  idx: '',
  name: '',
  surname: '',
  phone: '',
  degree: '',
  photo: '',
  working_since: '2020-01-01',
  faculty_id: '',
})

const s = ref({
  idx: '',
  name: '',
  surname: '',
  phone: '',
  photo: '',
  joined: new Date().toISOString().slice(0, 10),
  programme: '',
})

async function createTeacher() {
  await teacherApi.run(() =>
    admin.createTeacher({
      ...t.value,
      photo: t.value.photo || null,
    }),
  )
  await afterCreate(teacherApi)
}

async function createStudent() {
  await studentApi.run(() =>
    admin.createStudent({
      ...s.value,
      joined: `${s.value.joined}T00:00:00`,
      photo: s.value.photo || null,
    }),
  )
  await afterCreate(studentApi)
}
</script>

<template>
  <div>
    <h1 class="teacher-page-title">People</h1>
    <ApiMessages v-if="refsError" :error="refsError" />

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">New teacher</h2>
      <form class="admin-form" @submit.prevent="createTeacher">
        <label>Idx <input v-model="t.idx" required pattern="T[0-9]+" title="T followed by digits, e.g. T011" /></label>
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
        <label>Index number <input v-model="s.idx" required pattern="[0-9]+" title="Digits only" /></label>
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

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Enrol student in curriculum term</h2>
      <form class="admin-form" @submit.prevent="enrolStudent">
        <label>
          Student
          <select v-model="enrol.student_idx" required>
            <option value="" disabled>Select student</option>
            <option v-for="st in students" :key="st.idx" :value="st.idx">
              {{ st.idx }} {{ st.name }} {{ st.surname }}
            </option>
          </select>
        </label>
        <label>
          Curriculum term
          <select v-model="enrol.term_id" required>
            <option value="" disabled>Select term</option>
            <option v-for="t in terms" :key="t.id" :value="t.id">{{ t.label }}</option>
          </select>
        </label>
        <button type="submit" class="teacher-btn-save" :disabled="enrolApi.loading">Enrol</button>
      </form>
      <ApiMessages :error="enrolApi.error" :api-message="enrolApi.apiMessage" />
      <p v-if="enrolApi.result && !enrolApi.apiMessage" class="admin-ok">
        Enrolled {{ enrolApi.result.student_idx }}
      </p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">New administrator</h2>
      <form class="admin-form" @submit.prevent="createAdmin">
        <label>Idx <input v-model="a.idx" required pattern="A[0-9]+" title="A followed by digits, e.g. A002" /></label>
        <label>Name <input v-model="a.name" required /></label>
        <label>Surname <input v-model="a.surname" required /></label>
        <label>Phone <input v-model="a.phone" required /></label>
        <button type="submit" class="teacher-btn-save" :disabled="adminApi.loading">Create</button>
      </form>
      <ApiMessages :error="adminApi.error" :api-message="adminApi.apiMessage" />
      <p v-if="adminApi.result?.idx && !adminApi.apiMessage" class="admin-ok">
        Created administrator {{ adminApi.result.idx }}. Assign a login in User accounts.
      </p>
    </section>
  </div>
</template>
