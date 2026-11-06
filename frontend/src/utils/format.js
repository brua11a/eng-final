export const WEEKDAYS = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export function formatTime(t) {
  const m = t ? String(t).match(/(\d{1,2}):(\d{2})/) : null
  return m ? `${m[1].padStart(2, '0')}:${m[2]}` : ''
}

export function timeRange(start, end) {
  const s = formatTime(start)
  const e = formatTime(end)
  return s && e ? `${s}-${e}` : s || e
}

export function scheduleLine(weekday, start, end) {
  return [WEEKDAYS[weekday] || '', timeRange(start, end)].filter(Boolean).join(' ')
}

export function errorMessage(e) {
  return e?.detail || e?.message || String(e)
}

export function cycleLabel(c) {
  return `${c.year} ${c.season}`
}

export function teacherLabel(t) {
  return `${t.idx} ${t.surname} ${t.name}`
}
