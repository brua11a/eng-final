<script setup>
import { ref } from 'vue'
import { admin } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'

const api = useApiCall()
const studentIdx = ref('')
const groupId = ref('')
const teacherIdx = ref('')
const grade = ref(5)
const content = ref('')

function send() {
  api.run(() =>
    admin.createOpinion({
      student_idx: studentIdx.value,
      grade: Number(grade.value),
      content: content.value.trim() || null,
      group_id: groupId.value,
      teacher_idx: teacherIdx.value,
    }),
  )
}
</script>

<template>
  <div>
    <h1 class="teacher-page-title">Opinion</h1>

    <section class="teacher-panel admin-panel-spaced">
      <h2 class="admin-section-title">Submit for student</h2>
      <form class="admin-form" @submit.prevent="send">
        <label>Student idx <input v-model="studentIdx" required /></label>
        <label>Group id <input v-model="groupId" required /></label>
        <label>Teacher idx <input v-model="teacherIdx" required /></label>
        <label>Grade <input v-model="grade" type="number" step="0.5" min="2" max="5" required /></label>
        <label>Content <textarea maxlength="1000" v-model="content" rows="3" /></label>
        <button type="submit" class="teacher-btn-save" :disabled="api.loading">Submit</button>
      </form>
      <ApiMessages :error="api.error" :api-message="api.apiMessage" />
      <p v-if="api.result?.id && !api.apiMessage" class="admin-ok">Opinion {{ api.result.id }}</p>
    </section>
  </div>
</template>
