<script setup>
import { onMounted } from 'vue'
import { student } from '../../api/client'
import { useApiCall } from '../../composables/useApiCall'
import ApiMessages from '../../components/ApiMessages.vue'
import JsonPreview from '../../components/JsonPreview.vue'

const api = useApiCall()
onMounted(() => api.run(() => student.registeredGroups()))
</script>

<template>
  <div>
    <h1>Dashboard</h1>
    <button type="button" :disabled="api.loading" @click="api.run(() => student.registeredGroups())">
      GET /me/registered-groups
    </button>
    <ApiMessages :error="api.error" />
    <JsonPreview :data="api.result" />
  </div>
</template>
