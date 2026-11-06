<script setup>
import { onMounted, ref } from 'vue'
import { admin } from '../api/client'
import { errorMessage, teacherLabel } from '../utils/format'

const model = defineModel({ type: String, default: '' })
const emit = defineEmits(['ready'])
const teachers = ref([])
const error = ref('')

onMounted(async () => {
  try {
    const data = await admin.listTeachers()
    teachers.value = data?.teachers || []
    if (teachers.value.length && !teachers.value.some((t) => t.idx === model.value)) {
      model.value = teachers.value[0].idx
    }
  } catch (e) {
    error.value = errorMessage(e)
  }
  emit('ready')
})
</script>

<template>
  <div class="teacher-panel teacher-select">
    <label>
      Teacher
      <select v-model="model">
        <option v-for="t in teachers" :key="t.idx" :value="t.idx">{{ teacherLabel(t) }}</option>
      </select>
    </label>
    <span v-if="error" class="page-err">{{ error }}</span>
  </div>
</template>

<style scoped>
.teacher-select {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
  font-size: 0.82rem;
}

.teacher-select select {
  margin-left: 0.5rem;
  padding: 0.25rem 0.4rem;
}
</style>
