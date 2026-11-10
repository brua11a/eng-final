const DAY_MS = 86400000

export const WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']

export function parseTimeToMinutes(value) {
  if (value == null || value === '') return null
  if (typeof value === 'object' && value.hour != null && value.minute != null) {
    return Number(value.hour) * 60 + Number(value.minute)
  }
  const s = String(value)
  const m = s.match(/(\d{1,2}):(\d{2})/)
  if (!m) return null
  return Number(m[1]) * 60 + Number(m[2])
}

export function formatMinutes(m) {
  const h = Math.floor(m / 60)
  const min = m % 60
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`
}

export function startOfWeekMonday(date) {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + diff)
  return d
}

export function addDays(date, n) {
  return new Date(date.getTime() + n * DAY_MS)
}

export function weekRangeLabel(weekStart) {
  const end = addDays(weekStart, 4)
  const fmt = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return `${fmt(weekStart)} - ${fmt(end)}`
}

export function isoWeekNumber(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()))
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7))
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  return Math.ceil(((d - yearStart) / DAY_MS + 1) / 7)
}

export function pnpShowsThisWeek(pnp, weekStart) {
  const tag = String(pnp || 'ALL').toUpperCase()
  if (tag === 'ALL') return true
  const odd = isoWeekNumber(weekStart) % 2 === 1
  if (tag === 'P') return !odd
  if (tag === 'NP') return odd
  return true
}

function overlaps(a, b) {
  return a.startMin < b.endMin && b.startMin < a.endMin
}

function mergeClusters(clusters) {
  let merged = true
  while (merged) {
    merged = false
    for (let i = 0; i < clusters.length; i++) {
      for (let j = i + 1; j < clusters.length; j++) {
        const a = clusters[i]
        const b = clusters[j]
        if (a.some((x) => b.some((y) => overlaps(x, y)))) {
          clusters[i] = [...a, ...b]
          clusters.splice(j, 1)
          merged = true
          break
        }
      }
      if (merged) break
    }
  }
  return clusters
}

function assignColumns(cluster) {
  const sorted = [...cluster].sort((a, b) => a.startMin - b.startMin || a.endMin - b.endMin)
  const columns = []
  for (const ev of sorted) {
    let col = 0
    while (col < columns.length) {
      const last = columns[col][columns[col].length - 1]
      if (overlaps(last, ev)) col++
      else break
    }
    if (col === columns.length) columns.push([])
    columns[col].push(ev)
    ev.col = col
  }
  const colCount = columns.length
  for (const ev of sorted) {
    ev.colCount = colCount
  }
  return sorted
}

export function layoutDayEvents(rawEvents, gridStart, gridEnd) {
  const span = gridEnd - gridStart
  const events = rawEvents.map((e) => ({ ...e }))
  let clusters = events.map((e) => [e])
  clusters = mergeClusters(clusters)
  const laidOut = []
  for (const cluster of clusters) {
    assignColumns(cluster)
    for (const ev of cluster) {
      laidOut.push({
        ...ev,
        topPct: ((ev.startMin - gridStart) / span) * 100,
        heightPct: ((ev.endMin - ev.startMin) / span) * 100,
        leftPct: (ev.col / ev.colCount) * 100,
        widthPct: 100 / ev.colCount,
      })
    }
  }
  return laidOut
}

export function normalizeEntry(entry, role) {
  const startMin = parseTimeToMinutes(entry.start ?? entry.start_hr)
  const endMin = parseTimeToMinutes(entry.end ?? entry.end_time)
  const wdRaw = entry.weekday
  if (startMin == null || endMin == null || wdRaw == null || wdRaw === '') return null
  const wd = Number(wdRaw)
  if (!Number.isFinite(wd) || wd < 1 || wd > 5) return null
  const title = entry.course_name || entry.course_code || 'Class'
  const sub = [entry.g_type, entry.number != null ? `#${entry.number}` : entry.group_num != null ? `#${entry.group_num}` : '']
    .filter(Boolean)
    .join(' ')
  return {
    role,
    weekday: wd,
    startMin,
    endMin,
    pnp: entry.pnp || 'ALL',
    title,
    sub,
    room: entry.room || '',
    cycleStart: entry.cycle_start || null,
    cycleEnd: entry.cycle_end || null,
    label: `${title}${sub ? ` (${sub})` : ''}`,
  }
}

function isoDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// Classes are shown only on days inside their academic cycle's teaching period.
export function withinCycle(entry, weekStart) {
  // Anchor at noon so a DST shift in weekStart (built by adding 7*24h) cannot change the date.
  const d = new Date(weekStart.getTime() + 12 * 3600000)
  d.setDate(d.getDate() + entry.weekday - 1)
  const day = isoDate(d)
  if (entry.cycleStart && day < entry.cycleStart) return false
  if (entry.cycleEnd && day > entry.cycleEnd) return false
  return true
}

export function eventsForWeek(entries, weekStart, gridStart, gridEnd) {
  const byDay = [[], [], [], [], []]
  for (const e of entries) {
    if (!withinCycle(e, weekStart)) continue
    if (!pnpShowsThisWeek(e.pnp, weekStart)) continue
    if (e.endMin <= gridStart || e.startMin >= gridEnd) continue
    byDay[e.weekday - 1].push(e)
  }
  return byDay.map((list) => layoutDayEvents(list, gridStart, gridEnd))
}
