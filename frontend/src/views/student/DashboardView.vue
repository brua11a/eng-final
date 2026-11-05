<script setup>
import { onMounted } from 'vue'
import { student } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const api = useApiCall()
onMounted(() => api.run(() => student.dashboard()))
</script>

<template>
  <div>
    <h1>Dashboard</h1>
    <button type="button" :disabled="api.loading" @click="api.run(() => student.dashboard())">
      GET /me/dashboard
    </button>
    <ApiMessages :error="api.error" :api-message="api.apiMessage" />
    <JsonPreview :data="api.result" />
  </div>
</template>
