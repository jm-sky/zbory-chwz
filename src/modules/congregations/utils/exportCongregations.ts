import type { ICardContact, ICongregationDetailed } from '../types/congregation.types'
import { countryLabel, provinceLabel } from './geo'

export type ExportFormat = 'json' | 'markdown'

export const EXPORT_FORMAT_EXTENSION: Record<ExportFormat, string> = {
  json: 'json',
  markdown: 'md',
}

export const EXPORT_FORMAT_MIME: Record<ExportFormat, string> = {
  json: 'application/json',
  markdown: 'text/markdown',
}

/** Contacts, tolerating the legacy single-contact shape. */
export function contactsOf(congregation: ICongregationDetailed): ICardContact[] {
  if (congregation.card_contacts?.length) {
    return congregation.card_contacts.filter((contact) => contact.name)
  }
  if (congregation.contact_name) {
    return [{
      name: congregation.contact_name,
      title: congregation.contact_title,
      phone: congregation.contact_phone,
      email: congregation.contact_email,
    }]
  }
  return []
}

/** `zbory-chwz-2026-07-10.json` */
export function exportFilename(format: ExportFormat, now: Date = new Date()): string {
  const date = now.toISOString().slice(0, 10)
  return `zbory-chwz-${date}.${EXPORT_FORMAT_EXTENSION[format]}`
}

/** Markdown headings and field labels, supplied by the caller from i18n. */
export interface IExportLabels {
  title: string
  exportedAt: string
  count: string
  branchOf: string
  address: string
  serviceTimes: string
  contact: string
}

interface IExportOptions {
  locale: string
  labels: IExportLabels
  now?: Date
}

function toExportRecord(congregation: ICongregationDetailed, locale: string) {
  return {
    id: congregation.id,
    name: congregation.name,
    type: congregation.type ?? 'church',
    parentName: congregation.parent_name ?? null,
    description: congregation.description ?? null,
    status: congregation.status ?? null,
    address: {
      street: congregation.street ?? null,
      postalCode: congregation.postal_code ?? null,
      city: congregation.city ?? null,
      province: congregation.province ?? null,
      provinceLabel: congregation.province ? provinceLabel(congregation.province) : null,
      country: congregation.country ?? null,
      countryLabel: congregation.country ? countryLabel(congregation.country, locale) : null,
    },
    serviceTimes: congregation.service_times ?? [],
    contacts: contactsOf(congregation).map((contact) => ({
      name: contact.name ?? null,
      title: contact.title ?? null,
      phone: contact.phone ?? null,
      email: contact.email ?? null,
    })),
  }
}

export function toJson(
  congregations: ICongregationDetailed[],
  { locale, now = new Date() }: IExportOptions,
): string {
  const payload = {
    exportedAt: now.toISOString(),
    count: congregations.length,
    congregations: congregations.map((congregation) => toExportRecord(congregation, locale)),
  }
  return `${JSON.stringify(payload, null, 2)}\n`
}

function formatAddressLine(congregation: ICongregationDetailed, locale: string): string | null {
  const cityLine = [congregation.postal_code, congregation.city].filter(Boolean).join(' ')
  const region = [
    congregation.province ? provinceLabel(congregation.province) : null,
    congregation.country ? countryLabel(congregation.country, locale) : null,
  ]
    .filter(Boolean)
    .join(', ')

  const parts = [congregation.street, cityLine, region].filter(Boolean)
  return parts.length > 0 ? parts.join(', ') : null
}

function markdownSection(
  congregation: ICongregationDetailed,
  locale: string,
  labels: IExportLabels,
): string {
  const lines: string[] = [`## ${congregation.name}`, '']

  if (congregation.type === 'branch' && congregation.parent_name) {
    lines.push(`*${labels.branchOf}: ${congregation.parent_name}*`, '')
  }
  if (congregation.description) {
    lines.push(congregation.description, '')
  }

  const address = formatAddressLine(congregation, locale)
  if (address) {
    lines.push(`- **${labels.address}:** ${address}`)
  }

  const serviceTimes = congregation.service_times ?? []
  if (serviceTimes.length > 0) {
    const formatted = serviceTimes.map((time) => `${time.day} ${time.time}`).join(', ')
    lines.push(`- **${labels.serviceTimes}:** ${formatted}`)
  }

  for (const contact of contactsOf(congregation)) {
    const title = contact.title ? ` (${contact.title})` : ''
    const channels = [contact.phone, contact.email].filter(Boolean).join(', ')
    const suffix = channels ? ` — ${channels}` : ''
    lines.push(`- **${labels.contact}:** ${contact.name}${title}${suffix}`)
  }

  lines.push('')
  return lines.join('\n')
}

export function toMarkdown(
  congregations: ICongregationDetailed[],
  { locale, labels, now = new Date() }: IExportOptions,
): string {
  const header = [
    `# ${labels.title}`,
    '',
    `${labels.exportedAt}: ${now.toISOString().slice(0, 10)}`,
    `${labels.count}: ${congregations.length}`,
    '',
  ].join('\n')

  const body = congregations
    .map((congregation) => markdownSection(congregation, locale, labels))
    .join('\n')

  return `${header}\n${body}`
}

export function serializeCongregations(
  congregations: ICongregationDetailed[],
  format: ExportFormat,
  options: IExportOptions,
): string {
  return format === 'json' ? toJson(congregations, options) : toMarkdown(congregations, options)
}
