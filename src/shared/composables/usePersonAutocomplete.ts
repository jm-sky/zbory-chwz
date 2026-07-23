import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from 'vue-sonner'
import type { IPersonSummary } from '../types/person.type'
import { personSearchService } from '../services/personSearchService'

export interface PersonAutocompleteFields {
  firstName: string
  lastName: string
  email: string
  phone: string
}

const MIN_QUERY_LENGTH = 2
const DEBOUNCE_MS = 300

/**
 * Search-as-you-type matching against existing `persons`, driven by any of
 * the 4 free-text fields (first name / last name / email / phone). Selecting
 * a suggestion links `personId`; editing a field afterwards unlinks it again,
 * since the backend ignores the other fields once `personId` is set.
 */
export function usePersonAutocomplete() {
  const { t } = useI18n()

  const linkedPersonId = ref<string | null>(null)
  const suggestions = ref<IPersonSummary[]>([])
  const activeField = ref<keyof PersonAutocompleteFields | null>(null)
  const loading = ref(false)

  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let searchToken = 0

  function search(field: keyof PersonAutocompleteFields, query: string) {
    activeField.value = field
    if (debounceTimer) clearTimeout(debounceTimer)

    const trimmed = query.trim()
    if (trimmed.length < MIN_QUERY_LENGTH) {
      suggestions.value = []
      return
    }

    const token = ++searchToken
    debounceTimer = setTimeout(async () => {
      loading.value = true
      try {
        const results = await personSearchService.searchPersons(trimmed)
        if (token === searchToken) {
          suggestions.value = results
        }
      } catch {
        if (token === searchToken) suggestions.value = []
      } finally {
        if (token === searchToken) loading.value = false
      }
    }, DEBOUNCE_MS)
  }

  function handleFieldChange(field: keyof PersonAutocompleteFields, query: string) {
    if (linkedPersonId.value) {
      linkedPersonId.value = null
      toast.info(t('personSearch.editWarning', 'Edycja możliwa z poziomu przeglądarki osób'))
    }
    search(field, query)
  }

  function closeSuggestions() {
    suggestions.value = []
    activeField.value = null
  }

  function selectPerson(person: IPersonSummary): PersonAutocompleteFields {
    linkedPersonId.value = person.id
    closeSuggestions()
    return {
      firstName: person.firstName ?? '',
      lastName: person.lastName ?? '',
      email: person.email ?? '',
      phone: person.phone ?? '',
    }
  }

  function unlink() {
    linkedPersonId.value = null
  }

  function reset() {
    linkedPersonId.value = null
    suggestions.value = []
    activeField.value = null
    loading.value = false
  }

  return {
    linkedPersonId,
    suggestions,
    activeField,
    loading,
    handleFieldChange,
    closeSuggestions,
    selectPerson,
    unlink,
    reset,
  }
}
