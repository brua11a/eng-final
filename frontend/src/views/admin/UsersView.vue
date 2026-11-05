<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const assignApi = useApiCall()
const deactivateApi = useApiCall()
const activateApi = useApiCall()
const roleApi = useApiCall()
const removeRoleApi = useApiCall()

const email = ref('')
const passwd = ref('')
const idx = ref('')
const roleIdx = ref('')
const role = ref('Student')
const degree = ref('')
const workingSince = ref('')
const joined = ref(new Date().toISOString())

function assignUser() {
  assignApi.run(() => admin.assignUser({ email: email.value, passwd: passwd.value, idx: idx.value }))
}

function deactivate() {
  deactivateApi.run(() => admin.deactivateUser(idx.value))
}

function activate() {
  activateApi.run(() => admin.activateUser(idx.value))
}

function addRole() {
  const body = { idx: roleIdx.value, role: role.value }
  if (role.value === 'Teacher') {
    body.degree = degree.value
    body.working_since = workingSince.value
  }
  if (role.value === 'Student') body.joined = joined.value
  roleApi.run(() => admin.addRole(body))
}

function removeRole() {
  removeRoleApi.run(() => admin.removeRole({ idx: roleIdx.value, role: role.value }))
}
</script>

<template>
  <div>
    <h1>User accounts</h1>

    <section class="block">
      <h2>POST /admin/users</h2>
      <form class="form" @submit.prevent="assignUser">
        <input v-model="email" placeholder="email" required />
        <input v-model="passwd" placeholder="passwd" type="password" required />
        <input v-model="idx" placeholder="idx (person)" required />
        <button type="submit" :disabled="assignApi.loading">Assign user</button>
      </form>
      <ApiMessages :error="assignApi.error" :api-message="assignApi.apiMessage" />
      <JsonPreview :data="assignApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/users/deactivate & activate</h2>
      <input v-model="idx" placeholder="idx" />
      <div class="row">
        <button type="button" :disabled="deactivateApi.loading" @click="deactivate">Deactivate</button>
        <button type="button" :disabled="activateApi.loading" @click="activate">Activate</button>
      </div>
      <ApiMessages :error="deactivateApi.error" :api-message="deactivateApi.apiMessage" />
      <JsonPreview :data="deactivateApi.result" />
      <ApiMessages :error="activateApi.error" :api-message="activateApi.apiMessage" />
      <JsonPreview :data="activateApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/users/roles</h2>
      <form class="form" @submit.prevent="addRole">
        <input v-model="roleIdx" placeholder="idx" required />
        <select v-model="role">
          <option>Admin</option>
          <option>Teacher</option>
          <option>Student</option>
        </select>
        <template v-if="role === 'Teacher'">
          <input v-model="degree" placeholder="degree" required />
          <input v-model="workingSince" placeholder="working_since YYYY-MM-DD" required />
        </template>
        <template v-if="role === 'Student'">
          <input v-model="joined" placeholder="joined ISO datetime" required />
        </template>
        <button type="submit" :disabled="roleApi.loading">Add role</button>
      </form>
      <ApiMessages :error="roleApi.error" :api-message="roleApi.apiMessage" />
      <JsonPreview :data="roleApi.result" />
    </section>

    <section class="block">
      <h2>POST /admin/users/roles/remove</h2>
      <form class="form" @submit.prevent="removeRole">
        <input v-model="roleIdx" placeholder="idx" required />
        <select v-model="role">
          <option>Admin</option>
          <option>Teacher</option>
          <option>Student</option>
        </select>
        <button type="submit" :disabled="removeRoleApi.loading">Remove role</button>
      </form>
      <ApiMessages :error="removeRoleApi.error" :api-message="removeRoleApi.apiMessage" />
      <JsonPreview :data="removeRoleApi.result" />
    </section>
  </div>
</template>

<style scoped>
.block {
  margin-bottom: 2rem;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 24rem;
}
.row {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
</style>
