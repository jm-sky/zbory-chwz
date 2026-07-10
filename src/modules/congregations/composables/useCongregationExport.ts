import { useI18n } from 'vue-i18n'
import { downloadBlob } from '@/shared/utils/downloadBlob'
import type { ICongregationDetailed } from '../types/congregation.types'
import {
  EXPORT_FORMAT_MIME,
  exportFilename,
  type ExportFormat,
  type IExportLabels,
  serializeCongregations,
} from '../utils/exportCongregations'

export function useCongregationExport() {
  const { locale, t } = useI18n()

  function labels(): IExportLabels {
    return {
      title: t('congregations.export.title'),
      exportedAt: t('congregations.export.exportedAt'),
      count: t('congregations.export.count'),
      branchOf: t('congregations.export.branchOf'),
      address: t('congregations.export.address'),
      serviceTimes: t('congregations.export.serviceTimes'),
      contact: t('congregations.export.contact'),
    }
  }

  function buildMarkdownContent(congregations: ICongregationDetailed[]): string {
    return serializeCongregations(congregations, 'markdown', {
      locale: locale.value,
      labels: labels(),
    })
  }

  function downloadMarkdown(congregations: ICongregationDetailed[]): void {
    const content = buildMarkdownContent(congregations)
    const blob = new Blob([content], { type: `${EXPORT_FORMAT_MIME.markdown};charset=utf-8` })
    downloadBlob(blob, exportFilename('markdown'))
  }

  function exportCongregations(
    congregations: ICongregationDetailed[],
    format: ExportFormat,
  ): void {
    const content = serializeCongregations(congregations, format, {
      locale: locale.value,
      labels: labels(),
    })
    const blob = new Blob([content], { type: `${EXPORT_FORMAT_MIME[format]};charset=utf-8` })
    downloadBlob(blob, exportFilename(format))
  }

  return { buildMarkdownContent, downloadMarkdown, exportCongregations }
}
