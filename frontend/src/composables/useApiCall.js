import { reactive } from 'vue'
import { errorMessage } from '../utils/format'

export function useApiCall() {
  return reactive({
    loading: false,
    error: '',
    result: null,
    async run(fn) {
      this.loading = true
      this.error = ''
      try {
        const data = await fn()
        this.result = data
        return data
      } catch (e) {
        this.error = errorMessage(e)
        // Drop the previous result, so a success message is never shown next to an error.
        this.result = null
        return null
      } finally {
        this.loading = false
      }
    },
  })
}
