<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const api = useApiCall()
const parseError = ref('')

const name = ref('')
const cycleId = ref('')
const facultyId = ref('')
const regType = ref('zapisowa')
const turnsJson = ref(
  '[{"turn_number":1,"date":"2025-10-01","start":"08:00:00","end":"20:00:00"}]',
)
const groupIdsJson = ref('[]')

function submit() {
  parseError.value = ''
  let turns
  let group_ids
  try {
    turns = JSON.parse(turnsJson.value)
    group_ids = JSON.parse(groupIdsJson.value)
  } catch {
    parseError.value = 'Invalid JSON in turns or group_ids'
    return
  }
  api.run(() =>
    admin.startRegistrations({
      name: name.value,
      cycle_id: cycleId.value,
      faculty_id: facultyId.value,
      reg_type: regType.value,
      turns,
      group_ids,
    }),
  )
}
</script>

<template>
  <div>
    <h1>Start registrations</h1>
    <p class="hint">POST /admin/registrations</p>
    <form class="form" @submit.prevent="submit">
      <input v-model="name" placeholder="name" required />
      <input v-model="cycleId" placeholder="cycle_id" required />
      <input v-model="facultyId" placeholder="faculty_id" required />
      <input v-model="regType" placeholder="reg_type" required />
      <label>
        turns (JSON array)
        <textarea v-model="turnsJson" rows="4" />
      </label>
      <label>
        group_ids (JSON array of UUID strings)
        <textarea v-model="groupIdsJson" rows="2" />
      </label>
      <button type="submit" :disabled="api.loading">Start</button>
    </form>
    <ApiMessages :error="parseError || api.error" :api-message="api.apiMessage" />
    <JsonPreview :data="api.result" />
  </div>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 32rem;
}
textarea {
  font-family: monospace;
  font-size: 0.85rem;
}
.hint {
  color: #6b7280;
}
</style>
