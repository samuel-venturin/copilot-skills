---
name: refactor-pattern
description: Pattern Conformance sub-skill - Ensures files follow project-specific patterns and conventions documented in AGENTS.md.
---

# Pattern Sub-Skill: Project Pattern Conformance

Ensures all files conform to project-specific patterns and conventions documented in `AGENTS.md` and supporting documentation.

## What This Sub-Skill Does

- Reads `AGENTS.md` to understand project patterns
- References `e2e/docs/BEST_PRACTICES.md` for E2E patterns
- Detects pattern deviations in any file type
- Suggests standardized refactoring
- Applies patterns consistently across codebase

## Pattern Sources

### 1. AGENTS.md
Main project conventions file that documents:
- Component architecture patterns
- Naming conventions
- Import styles
- State management patterns
- Testing requirements

### 2. e2e/docs/
E2E testing patterns:
- `BEST_PRACTICES.md` — 11 non-negotiable rules (R01-R11)
- `ARCHITECTURE.md` — POM structure and organization
- `QUICK_START.md` — test setup patterns

### 3. ai-base-rules/frontend/
External pattern repository with:
- Component organization (`04-architecture-patterns/`)
- Nuxt patterns (`02-nuxt-framework/`)
- Testing guidelines (`05-testing/`)

## Typical Pattern Violations

### Vue Components
```vue
<!-- ❌ WRONG: Options API -->
<script>
export default {
  data() { ... },
  methods: { ... }
}
</script>

<!-- ✅ RIGHT: Composition API with <script setup> -->
<script setup lang="ts">
// logic here
</script>
```

### E2E Tests - Selectors
```typescript
// ❌ WRONG: Using data-test
await page.locator('[data-test="customer-list"]').click();

// ✅ RIGHT: Only data-testid
await page.locator('[data-testid="customer-list"]').click();
```

### E2E Tests - Navigation Rule R01
```typescript
// ❌ WRONG: Direct goto() bypass (except setup/smoke)
await page.goto('/customer/123/edit');

// ✅ RIGHT: Navigate via UI
await page.goto('/customer/list');
const editButton = page.locator('[data-testid="edit-button"]').first();
await editButton.click();
```

### E2E Tests - Waits (Rule R07)
```typescript
// ❌ WRONG: Fixed timeout
await page.waitForTimeout(3000);

// ✅ RIGHT: Conditional wait
await page.waitForSelector('[data-testid="form"]');
```

### E2E Tests - Naming (Rule R09)
```typescript
// ❌ WRONG: Generic names
test('customer crud', async () => { ... })
test('edit test', async () => { ... })

// ✅ RIGHT: Behavior-driven naming
test('should load customer list when page initializes', async () => { ... })
test('should update customer when form submitted successfully', async () => { ... })
```

### Import Style
```javascript
// ❌ WRONG: CommonJS
const utils = require('./utils');
const { helper } = require('./helpers');

// ✅ RIGHT: ESM
import { utils } from './utils';
import { helper } from './helpers';
```

### Naming Conventions
```javascript
// ❌ WRONG: Mixed conventions
const user_name = 'John';    // snake_case
const userEmail = 'john@...'; // camelCase
const TEMP = 'data';         // SCREAMING but not constant

// ✅ RIGHT: Consistent
const firstName = 'John';        // camelCase
const emailAddress = 'john@...'; // camelCase
const API_KEY = env.KEY;         // SCREAMING for constants
```

## E2E Pattern Rules Summary

From `e2e/docs/BEST_PRACTICES.md`:

| Rule | Violation | Fix |
|------|-----------|-----|
| R01 | Direct `page.goto()` in tests | Navigate via UI (clicks) |
| R02 | Unclean test code | Apply SOLID, DRY, FP |
| R03 | Mocked APIs | Test against real API |
| R04 | Mocks without env flag | Add `E2E_MOCK_*=true` |
| R05 | Shared test state | Full isolation, any order |
| R06 | `data-test` in selectors | Use `data-testid` only |
| R07 | `waitForTimeout()` | Use conditional waits |
| R08 | Inline test data | Use factories in `e2e/data/factories/` |
| R09 | Generic test names | Use "should X when Y" pattern |
| R10 | @smoke tests modify data | Make @smoke read-only |
| R11 | Altering test to pass | Fix source code instead |

## Output Format

```markdown
---
feature: customer
arquivo: e2e/tests/customer/list.spec.ts
tipo: pattern (Project Pattern Conformance)
arquivos_relacionados: e2e/docs/BEST_PRACTICES.md, AGENTS.md
porque: Garantir consistência com padrões do projeto
---

# customer-list-pattern.spec

## Padrões violados
1. Seletor usa `data-test` ao invés de `data-testid` (R06)
   - Linhas: 45, 67, 89, 123

2. Navegação direto com `page.goto()` fora de setup (R01)
   - Linha: 156

3. Nome de teste não segue "should X when Y" (R09)
   - Linhas: 78 ("customer crud"), 95 ("edit test")

## Por que mudar
- Manter consistência com BEST_PRACTICES.md
- Garantir que testes sigam padrões corporativos
- Preparar para integração com Playwright automatizado

## Como
1. Substituir `data-test="..."` por `data-testid="..."`
2. Mover navegação para step anterior via UI
3. Renomear testes com padrão "should {behavior} when {condition}"

## Onde
- Linhas 45, 67, 89, 123 (selectors)
- Linha 156 (navigation)
- Linhas 78, 95 (naming)

## O que
[Código refatorado com padrões conformes]
```
