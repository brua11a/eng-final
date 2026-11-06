import { reactive } from 'vue'
import { errorMessage } from '../utils/format'

export function useApiCall() {
  return reactive({
    loading: false,
    error: '',
    result: null,
    apiMessage: '',
    async run(fn) {
      this.loading = true
      this.error = ''
      this.apiMessage = ''
      try {
        const data = await fn()
        this.result = data
        this.apiMessage = data?._apiMessage || ''
        return data
      } catch (e) {
        this.error = errorMessage(e)
        return null
      } finally {
        this.loading = false
      }
    },
  })
}
