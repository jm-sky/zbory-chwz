/** Display format for an IBAN stored in canonical form (country prefix, no spaces, upper case).
 *
 * Polish accounts display in the domestic NRB style (no "PL" prefix, first group
 * is 2 digits): "61 1090 1014 0000 0712 1981 2874". Every other country displays
 * as a standard IBAN (country prefix kept, grouped in 4s from the start).
 */
export const formatIban = (iban: string | null | undefined): string => {
  if (!iban) return ''

  const cleaned = iban.replace(/[\s-]/g, '').toUpperCase()

  if (cleaned.startsWith('PL')) {
    const nrb = cleaned.slice(2)
    const groups = [nrb.slice(0, 2), ...nrb.slice(2).match(/.{1,4}/g) ?? []]
    return groups.join(' ')
  }

  return cleaned.match(/.{1,4}/g)?.join(' ') ?? cleaned
}
