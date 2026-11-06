<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'

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
const joined = ref(new Date().toISOString().slice(0, 10))

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
  if (role.value === 'Student') body.joined = `${joined.value}T00:00:00`
  roleApi.run(() => admin.addRole(body))
}

function removeRole() {
  removeRoleApi.run(() => admin.removeRole({ idx: roleIdx.value, role: role.value }))
}

function rolesText(res) {
  if (!res?.roles?.length) return ''
  return res.roles.join(', ')
}
</script>

<template>
  <div>
    <h1 class="teacher-page-title">User accounts</h1>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Assign login</h2>
      <form class="admin-form" @submit.prevent="assignUser">
        <label>
          Email
          <input v-model="email" type="email" required />
        </label>
        <label>
          Password
          <input v-model="passwd" type="password" required />
        </label>
        <label>
          Person idx
          <input v-model="idx" required />
        </label>
        <button type="submit" class="teacher-btn-save" :disabled="assignApi.loading">Save</button>
      </form>
      <ApiMessages :error="assignApi.error" :api-message="assignApi.apiMessage" />
      <p v-if="assignApi.result && !assignApi.apiMessage" class="admin-ok">
        {{ assignApi.result.email }}, roles: {{ rolesText(assignApi.result) || 'none' }}
      </p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Activate / deactivate</h2>
      <div class="admin-form">
        <label>
          Person idx
          <input v-model="idx" />
        </label>
        <div class="admin-form-row">
          <button type="button" class="teacher-btn-secondary" :disabled="deactivateApi.loading" @click="deactivate">
            Deactivate
          </button>
          <button type="button" class="teacher-btn-secondary" :disabled="activateApi.loading" @click="activate">
            Activate
          </button>
        </div>
      </div>
      <ApiMessages :error="deactivateApi.error" :api-message="deactivateApi.apiMessage" />
      <ApiMessages :error="activateApi.error" :api-message="activateApi.apiMessage" />
      <p v-if="deactivateApi.result && !deactivateApi.apiMessage" class="admin-ok">
        Deactivated {{ deactivateApi.result.idx }}
      </p>
      <p v-if="activateApi.result && !activateApi.apiMessage" class="admin-ok">
        Activated {{ activateApi.result.idx }}
      </p>
    </section>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Roles</h2>
      <form class="admin-form" @submit.prevent="addRole">
        <label>
          Person idx
          <input v-model="roleIdx" required />
        </label>
        <label>
          Role
          <select v-model="role">
            <option>Admin</option>
            <option>Teacher</option>
            <option>Student</option>
          </select>
        </label>
        <template v-if="role === 'Teacher'">
          <label>
            Degree
            <input v-model="degree" required />
          </label>
          <label>
            Working since
            <input v-model="workingSince" type="date" required />
          </label>
        </template>
        <template v-if="role === 'Student'">
          <label>
            Joined
            <input v-model="joined" type="date" required />
          </label>
        </template>
        <button type="submit" class="teacher-btn-save" :disabled="roleApi.loading">Add role</button>
      </form>
      <ApiMessages :error="roleApi.error" :api-message="roleApi.apiMessage" />
      <p v-if="roleApi.result && !roleApi.apiMessage" class="admin-ok">
        Roles: {{ rolesText(roleApi.result) }}
      </p>

      <form class="admin-form admin-form--divided" @submit.prevent="removeRole">
        <button type="submit" class="teacher-btn-secondary" :disabled="removeRoleApi.loading">Remove selected role</button>
      </form>
      <ApiMessages :error="removeRoleApi.error" :api-message="removeRoleApi.apiMessage" />
      <p v-if="removeRoleApi.result && !removeRoleApi.apiMessage" class="admin-ok">
        Roles: {{ rolesText(removeRoleApi.result) }}
      </p>
    </section>
  </div>
</template>
