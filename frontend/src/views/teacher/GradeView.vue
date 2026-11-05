<script setup>
import { ref } from 'vue'
import { teacher } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const api = useApiCall()
const groupId = ref('')
const studentIdx = ref('')
const grade = ref(3)

function submit() {
  api.run(() => teacher.setGrade(groupId.value, studentIdx.value, Number(grade.value)))
}
</script>

<template>
  <div>
    <h1>Set group grade</h1>
    <p class="hint">Official mark on REGISTERED_IN (not an opinion).</p>
    <form class="form" @submit.prevent="submit">
      <label>group_id <input v-model="groupId" required /></label>
      <label>student_idx <input v-model="studentIdx" required /></label>
      <label>grade <input v-model="grade" type="number" step="0.1" required /></label>
      <button type="submit" :disabled="api.loading">POST /groups/students/grade</button>
    </form>
    <ApiMessages :error="api.error" :api-message="api.apiMessage" />
    <JsonPreview :data="api.result" />
  </div>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 24rem;
}
label {
  display: flex;
  flex-direction: column;
}
.hint {
  color: #6b7280;
  font-size: 0.9rem;
}
</style>
