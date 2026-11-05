import { reactive } from 'vue'
import { ApiError } from '../api/client'

/**
 * Reactive API call state for templates (`state.loading`, `@click="state.run(...)"`).
 * Returned as a reactive object so :disabled bindings unwrap correctly (plain Ref bags do not).
 */
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
      this.result = null
      try {
        const data = await fn()
        this.result = data
        if (data?._apiMessage) this.apiMessage = data._apiMessage
        if (data?.err) this.apiMessage = data.err
        if (data?.ok === false && data?.err) this.apiMessage = data.err
        return data
      } catch (e) {
        if (e instanceof ApiError) {
          this.error = e.detail || e.message
        } else {
          this.error = e?.message || String(e)
        }
        throw e
      } finally {
        this.loading = false
      }
    },
  })
}
