<script setup>
import { onMounted, ref } from 'vue'
import { student } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const listApi = useApiCall()
const coursesApi = useApiCall()
const groupsApi = useApiCall()
const registerApi = useApiCall()

const selectedRegistrationId = ref('')
const selectedCourseId = ref('')
const registerGroupId = ref('')

onMounted(() => {
  listApi.run(() => student.registrations())
})

function loadCourses() {
  coursesApi.run(() => student.registrationCourses(selectedRegistrationId.value))
}

function loadGroups() {
  groupsApi.run(() =>
    student.registrationGroups(selectedRegistrationId.value, selectedCourseId.value),
  )
}

function register() {
  registerApi.run(() => student.register(selectedCourseId.value, registerGroupId.value))
}
</script>

<template>
  <div>
    <h1>Registration flow</h1>
    <p class="hint">List → courses → groups → register</p>

    <section class="block">
      <h2>GET /me/registrations</h2>
      <button type="button" :disabled="listApi.loading" @click="listApi.run(() => student.registrations())">
        Refresh
      </button>
      <ApiMessages :error="listApi.error" :api-message="listApi.apiMessage" />
      <JsonPreview :data="listApi.result" />
    </section>

    <section class="block">
      <h2>POST /me/registrations/courses</h2>
      <form class="row" @submit.prevent="loadCourses">
        <input v-model="selectedRegistrationId" placeholder="registration_id" required />
        <button type="submit" :disabled="coursesApi.loading">Load courses</button>
      </form>
      <ApiMessages :error="coursesApi.error" :api-message="coursesApi.apiMessage" />
      <JsonPreview :data="coursesApi.result" />
    </section>

    <section class="block">
      <h2>POST /me/registrations/groups</h2>
      <form class="row" @submit.prevent="loadGroups">
        <input v-model="selectedRegistrationId" placeholder="registration_id" required />
        <input v-model="selectedCourseId" placeholder="course_id (subject instance id)" required />
        <button type="submit" :disabled="groupsApi.loading">Load groups</button>
      </form>
      <ApiMessages :error="groupsApi.error" :api-message="groupsApi.apiMessage" />
      <JsonPreview :data="groupsApi.result" />
    </section>

    <section class="block">
      <h2>POST /me/registrations/register</h2>
      <form class="row" @submit.prevent="register">
        <input v-model="selectedCourseId" placeholder="course_id" required />
        <input v-model="registerGroupId" placeholder="group_id" required />
        <button type="submit" :disabled="registerApi.loading">Register</button>
      </form>
      <ApiMessages :error="registerApi.error" :api-message="registerApi.apiMessage" />
      <JsonPreview :data="registerApi.result" />
    </section>
  </div>
</template>

<style scoped>
.block {
  margin-bottom: 1.5rem;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
input,
button {
  padding: 0.4rem 0.5rem;
}
.hint {
  color: #6b7280;
  font-size: 0.9rem;
}
</style>
