export const formatPhoneNumber = (phone: string | null | undefined): string => {
  if (!phone) return ''

  const digits = phone.replace(/\D/g, '')

  if (digits.length === 11 && digits.startsWith('48')) {
    const national = digits.slice(2)
    return `+48 ${national.slice(0, 3)} ${national.slice(3, 6)} ${national.slice(6, 9)}`
  }

  if (digits.length === 9) {
    return `+48 ${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6, 9)}`
  }

  return phone
}
