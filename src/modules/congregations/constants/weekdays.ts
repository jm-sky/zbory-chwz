/** Canonical weekday order for service times, starting from Sunday. */
export const WEEKDAY_KEYS = [
  'sunday',
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
] as const

export type WeekdayKey = typeof WEEKDAY_KEYS[number]

interface WeekdayEntry {
  key: WeekdayKey
  order: number
  /** Recognized free-text values (lowercase) that match this weekday, for sorting/autocomplete. */
  names: string[]
}

const WEEKDAYS: WeekdayEntry[] = [
  { key: 'sunday', order: 0, names: ['niedziela', 'sunday'] },
  { key: 'monday', order: 1, names: ['poniedziałek', 'poniedzialek', 'monday'] },
  { key: 'tuesday', order: 2, names: ['wtorek', 'tuesday'] },
  { key: 'wednesday', order: 3, names: ['środa', 'sroda', 'wednesday'] },
  { key: 'thursday', order: 4, names: ['czwartek', 'thursday'] },
  { key: 'friday', order: 5, names: ['piątek', 'piatek', 'friday'] },
  { key: 'saturday', order: 6, names: ['sobota', 'saturday'] },
]

/** Sort order for a free-text day value; unrecognized values sort after all known weekdays. */
export function getWeekdayOrder(day: string): number {
  const normalized = day.trim().toLowerCase()
  const match = WEEKDAYS.find(w => w.names.includes(normalized))
  return match ? match.order : WEEKDAYS.length
}
