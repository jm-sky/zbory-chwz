# [ID: Nazwa] - Analiza

**Phase:** A (Backend) / B (Frontend) / C (Integration)
**Data:** YYYY-MM-DD
**Zakres:** `path/to/analyzed/code`
**Status:** 🔄 In Progress / ✅ Completed
**Language/Stack:** Python/FastAPI / TypeScript/Vue 3 / Integration

---

## 1. Overview

### Struktura katalogów
```
analyzed/path/
├── file1.py / file1.ts
├── file2.py / file2.ts
└── subdirectory/
    └── file3.py / file3.ts
```

### Kluczowe pliki
- **`file1.py/ts`** - Opis przeznaczenia
- **`file2.py/ts`** - Opis przeznaczenia

### Statystyki
- Liczba plików: X
- Łączne linie kodu: ~X
- Główne dependencies: X, Y, Z
- Language-specific metrics (e.g., Python: modules, TypeScript: components/composables)

---

## 2. SOLID Analysis

### ✅ Single Responsibility Principle (SRP)

#### Violations
- [ ] **[CRITICAL]** `FileName.ts:LineNumber` - Klasa/funkcja ma zbyt wiele odpowiedzialności
  - **Problem:** Opis problemu
  - **Impact:** Wysoki/Średni/Niski
  - **Recommendation:** Konkretna rekomendacja

#### Good Practices
- ✅ `FileName.ts:LineNumber` - Przykład dobrej praktyki

---

### ✅ Open/Closed Principle (OCP)

#### Violations
- [ ] **[HIGH]** `FileName.ts:LineNumber` - Kod wymaga modyfikacji zamiast rozszerzenia
  - **Problem:** Opis problemu
  - **Recommendation:** Sugestia abstrakcji/interfejsu

#### Good Practices
- ✅ Przykłady extensibility

---

### ✅ Liskov Substitution Principle (LSP)

#### Issues
- [ ] Problemy z substitution (jeśli występują)

---

### ✅ Interface Segregation Principle (ISP)

#### Violations
- [ ] **[MEDIUM]** `FileName.ts:LineNumber` - Interface za duży/zbyt ogólny
  - **Problem:** Opis problemu
  - **Recommendation:** Split interface

#### Good Practices
- ✅ Małe, spójne interfejsy

---

### ✅ Dependency Inversion Principle (DIP)

#### Violations
- [ ] **[HIGH]** `FileName.ts:LineNumber` - Zależność od konkretnej implementacji
  - **Problem:** Tight coupling
  - **Recommendation:** Depend on abstraction

---

## 3. KISS Analysis (Keep It Simple)

### Over-Engineering
- [ ] **[MEDIUM]** `FileName.ts:LineNumber` - Unnecessarily complex solution
  - **Problem:** Opis zbyt skomplikowanego rozwiązania
  - **Simpler approach:** Propozycja prostszego rozwiązania

### Unnecessary Abstractions
- [ ] Abstrakcje, które nie są potrzebne

### Good Practices
- ✅ Przykłady prostych, czytelnych rozwiązań

---

## 4. DRY Analysis (Don't Repeat Yourself)

### Code Duplication

#### Critical Duplications (3+ miejsca)
- [ ] **[CRITICAL]** Duplicated logic w `File1.ts:Line`, `File2.ts:Line`, `File3.ts:Line`
  - **Pattern:** Opis powtarzającego się wzorca
  - **Recommendation:** Extract to utility/composable
  - **Location:** `path/to/suggested/extraction.ts`

#### Moderate Duplications (2 miejsca)
- [ ] **[MEDIUM]** Similar code w `File1.ts:Line`, `File2.ts:Line`
  - **Pattern:** Opis podobnego kodu
  - **Recommendation:** Consider extraction

### Similar Patterns
- Wzorce, które mogłyby być zunifikowane

### Good Practices
- ✅ Przykłady good DRY practices

---

## 5. Modularity Analysis

### Separation of Concerns

#### Issues
- [ ] **[HIGH]** `FileName.ts` - Mixed concerns
  - **Problem:** Business logic + UI logic + data fetching
  - **Recommendation:** Split into separate files/functions

#### Good Practices
- ✅ Przykłady dobrej separacji

---

### Module Coupling

#### Tight Coupling
- [ ] **[HIGH]** `ModuleA` → `ModuleB` (tight dependency)
  - **Problem:** Opis problemu
  - **Recommendation:** Introduce interface/event bus

#### Loose Coupling
- ✅ Przykłady loose coupling

---

### Reusability

#### Low Reusability
- [ ] **[MEDIUM]** `Component.vue` - Could be more reusable
  - **Problem:** Hardcoded values, specific use case
  - **Recommendation:** Add props, make generic

#### High Reusability
- ✅ Komponenty/funkcje z dobrą reusability

---

## 6. Code Splitting Opportunities

### Large Functions
- [ ] **[HIGH]** `FileName.ts:FunctionName` (~X lines)
  - **Current complexity:** Cyclomatic complexity = X
  - **Split into:**
    1. `helperFunction1()` - Opis
    2. `helperFunction2()` - Opis
    3. `helperFunction3()` - Opis

### Complex Components
- [ ] **[MEDIUM]** `Component.vue` (~X lines)
  - **Split into:**
    1. `SubComponent1.vue` - Opis
    2. `SubComponent2.vue` - Opis

### Shared Logic
- [ ] **[MEDIUM]** Logic that could be extracted to composable/utility
  - **From:** `File1.ts`, `File2.ts`
  - **To:** `useSharedLogic()` composable or `sharedUtil()` function

---

## 7. Additional Findings

### Performance Issues
- [ ] Potencjalne problemy z performance
- [ ] **Backend:** N+1 queries, missing indexes, inefficient SQLAlchemy usage
- [ ] **Frontend:** Unnecessary re-renders, large bundle sizes, missing lazy loading

### Type Safety
- [ ] **Backend:** Missing type hints, `Any` usage, weak Pydantic schemas
- [ ] **Frontend:** `any` types that could be more specific, missing type definitions

### Error Handling
- [ ] Missing error handling
- [ ] Inconsistent error handling patterns
- [ ] **Backend:** Missing custom exceptions, poor error messages
- [ ] **Frontend:** Uncaught promise rejections, missing error boundaries

### Testing Gaps
- [ ] Kod bez testów (jeśli krytyczny)
- [ ] **Backend:** Missing unit tests for services/repositories
- [ ] **Frontend:** Missing component tests, composable tests

### Documentation
- [ ] **Backend:** Missing docstrings for public functions/classes
- [ ] **Frontend:** Missing JSDoc comments for complex functions
- [ ] Unclear naming

### Security Concerns (if applicable)
- [ ] **Backend:** SQL injection risks, missing input validation, weak authentication
- [ ] **Frontend:** XSS vulnerabilities, sensitive data exposure, insecure API calls

---

## 8. Findings Summary

### Critical (Must Fix)
| Priority | File | Issue | Impact |
|----------|------|-------|--------|
| 🔴 | `file.ts:line` | Problem description | High |

### High (Should Fix)
| Priority | File | Issue | Impact |
|----------|------|-------|--------|
| 🟠 | `file.ts:line` | Problem description | Medium-High |

### Medium (Nice to Have)
| Priority | File | Issue | Impact |
|----------|------|-------|--------|
| 🟡 | `file.ts:line` | Problem description | Medium |

### Low (Optional)
| Priority | File | Issue | Impact |
|----------|------|-------|--------|
| 🟢 | `file.ts:line` | Problem description | Low |

---

## 9. Refactoring Recommendations

### Phase 1: Critical Fixes (Effort: X days)
1. **Task name**
   - **Files:** `file1.ts`, `file2.ts`
   - **Action:** Konkretny opis akcji
   - **Benefits:** Jakie korzyści przyniesie
   - **Risks:** Potencjalne ryzyka

### Phase 2: High Priority (Effort: X days)
2. **Task name**
   - **Files:** `file.ts`
   - **Action:** Opis
   - **Benefits:** Korzyści

### Phase 3: Medium Priority (Effort: X days)
3. **Task name**
   - **Files:** `file.ts`
   - **Action:** Opis

### Phase 4: Low Priority (Effort: X days)
4. **Task name**
   - **Files:** `file.ts`
   - **Action:** Opis

---

## 10. Dependencies & Blockers

### Dependencies
- This refactoring depends on: [List other refactorings]

### Blockers
- Potential blockers: [Technical/business constraints]

---

## 11. Next Steps

1. [ ] Review findings with team
2. [ ] Prioritize refactoring tasks
3. [ ] Create GitHub issues/tickets
4. [ ] Schedule refactoring work

---

## 12. Notes & Observations

- Dodatkowe obserwacje
- Wzorce zauważone podczas analizy
- Pytania do zespołu

---

*Analiza przeprowadzona przez: Claude Code*
*Data: YYYY-MM-DD*
