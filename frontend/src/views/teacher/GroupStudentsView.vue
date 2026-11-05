<script setup>
import { ref } from 'vue'
import { teacher } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const api = useApiCall()
const groupId = ref('')

function load() {
  api.run(() => teacher.groupStudents(groupId.value))
}
</script>

<template>
  <div>
    <h1>Students in group</h1>
    <form class="row" @submit.prevent="load">
      <input v-model="groupId" placeholder="group_id" required />
      <button type="submit" :disabled="api.loading">POST /groups/students</button>
    </form>
    <ApiMessages :error="api.error" :api-message="api.apiMessage" />
    <JsonPreview :data="api.result" />
  </div>
</template>

<style scoped>
.row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
