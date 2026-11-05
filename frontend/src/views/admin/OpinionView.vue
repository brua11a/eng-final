<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const api = useApiCall()
const studentIdx = ref('')
const groupId = ref('')
const grade = ref(5)
const content = ref('')
const submit = ref(new Date().toISOString())

function send() {
  api.run(() =>
    admin.createOpinion({
      student_idx: studentIdx.value,
      grade: Number(grade.value),
      content: content.value || null,
      submit: submit.value,
      group_id: groupId.value,
    }),
  )
}
</script>

<template>
  <div>
    <h1>Opinion (for student)</h1>
    <p class="hint">POST /opinions with student_idx (admin filing for another student).</p>
    <form class="form" @submit.prevent="send">
      <label>student_idx <input v-model="studentIdx" required /></label>
      <label>group_id <input v-model="groupId" required /></label>
      <label>grade <input v-model="grade" type="number" step="0.1" required /></label>
      <label>content <input v-model="content" /></label>
      <label>submit <input v-model="submit" required /></label>
      <button type="submit" :disabled="api.loading">Submit</button>
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
  max-width: 28rem;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.hint {
  color: #6b7280;
  font-size: 0.9rem;
}
</style>
