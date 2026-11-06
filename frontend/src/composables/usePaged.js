import { computed, ref } from 'vue'

export function usePaged(rows, pageSize = 30) {
  const page = ref(1)
  const pageCount = computed(() => Math.max(1, Math.ceil(rows.value.length / pageSize)))
  const pageRows = computed(() => {
    const start = (page.value - 1) * pageSize
    return rows.value.slice(start, start + pageSize)
  })
  return { page, pageCount, pageRows }
}
