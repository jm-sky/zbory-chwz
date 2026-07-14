interface IAddressLike {
  street?: string | null
  city?: string | null
  postal_code?: string | null
}

export function formatAddress(congregation: IAddressLike): string {
  const parts: string[] = []
  if (congregation.street) parts.push(congregation.street)
  if (congregation.postal_code && congregation.city) {
    parts.push(`${congregation.postal_code} ${congregation.city}`)
  } else if (congregation.city) {
    parts.push(congregation.city)
  }
  return parts.join(', ') || ''
}

export function formatServiceTimes(serviceTimes?: Array<{ day: string; time: string; description?: string | null }>): string {
  if (!serviceTimes || serviceTimes.length === 0) return ''
  return serviceTimes
    .map((st) => st.description ? `${st.day} ${st.time} - ${st.description}` : `${st.day} ${st.time}`)
    .join(', ')
}
