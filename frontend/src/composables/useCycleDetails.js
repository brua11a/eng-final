import { ref } from 'vue'
import { student } from '../api/client'
import { errorMessage } from '../utils/format'

export function useCycleDetails() {
  const details = ref({})
  const loadingId = ref('')
  const errors = ref({})

  async function ensure(cycleId) {
    if (!cycleId || details.value[cycleId]) return
    loadingId.value = cycleId
    errors.value = { ...errors.value, [cycleId]: '' }
    try {
      const data = await student.academicCycleDetail(cycleId)
      details.value = { ...details.value, [cycleId]: data }
    } catch (e) {
      errors.value = { ...errors.value, [cycleId]: errorMessage(e) }
    } finally {
      loadingId.value = ''
    }
  }

  return { details, loadingId, errors, ensure }
}
