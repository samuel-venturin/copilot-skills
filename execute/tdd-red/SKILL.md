---
name: execute-tdd-red
description: TDD-RED phase — Write all unit and E2E tests FIRST (in failing state) based on QUALITY.md acceptance criteria. Tests document the expected behavior before implementation begins.
---

# /execute-tdd-red — Test-First (TDD-RED) Phase

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`

Input (from `/execute-setup` output):
- `$TICKET` — task ID
- `$WORKTREE_PATH` — worktree path
- `$QUALITY_PATH` — `/docs/tasks/<TICKET>/QUALITY.md`
- `$PROMPT_PATH` — `/docs/tasks/<TICKET>/PROMPT.md`

---

## Overview

This phase implements the **RED phase of TDD** — writing comprehensive unit tests and E2E tests **before any implementation begins**. Tests serve as **executable documentation** of what the feature must do.

**Mandatory dependencies:**
- QUALITY.md file with acceptance criteria and test case definitions
- `<WORKTREE_PATH>/AGENTS.md` for testing and engineering standards (source of truth)
- E2E docs (`e2e/docs/ARCHITECTURE.md`, `e2e/docs/QUICK_START.md`)
- Project test patterns (Vitest, Vue Test Utils, Playwright)
- E2E protocol: check app availability on `localhost:3001..3005`, run headed mode, request manual auth if Keycloak is reached
- E2E automation source-of-truth: `<WORKTREE_PATH>/e2e/tests/<dominio>`
- **Protocolo djalma descontinuado: não usar**

**Test categories to write:**
1. **Unit Tests** — Component props, events, state, validation logic
2. **E2E Tests** — Full user workflows, navigation, form submissions
3. **Integration Tests** — Component + API interactions (if applicable)

---

## Step 1 — Read QUALITY.md & Extract Test Cases

```bash
cd $WORKTREE_PATH
cat $QUALITY_PATH
```

Extract and categorize:
- **Unit Test Cases** — TC-01, TC-02, ... (marked as "Unit Test Cases")
- **E2E Test Cases** — E2E-01, E2E-02, ... (marked as "E2E Test Cases")
- **Regression Checklist** — Tests to ensure no breaking changes
- **Definition of Done** — Final acceptance criteria
- **E2E domain path** — map to `<WORKTREE_PATH>/e2e/tests/<dominio>` based on task scope

Store in structured format:
```json
{
  "ticket": "<TICKET>",
  "test_cases": {
    "unit": [
      {
        "id": "TC-01",
        "title": "TaxRegimeSelect shows required asterisk",
        "assertions": ["Label contains asterisk", "Matches visual style"]
      }
    ],
    "e2e": [
      {
        "id": "E2E-01",
        "title": "Save without tax regime — inline error",
        "steps": ["Navigate", "Ensure not selected", "Click Save", "Verify error"]
      }
    ],
    "regression": [...]
  }
}
```

If QUALITY.md is **missing or incomplete**:
> "⛔ QUALITY.md está ausente ou incompleto para `<TICKET>`.
> Essa fase requer teste cases bem definidos.
> Consulte `/interpret <TICKET>` para regenerar os artefatos."

**STOP. Do not continue without complete QUALITY.md.**

---

## Step 2 — Dispatch João (Frontend Engineer) for Test Writing

Build context and dispatch João for **test-first implementation**. João's role: write all tests in RED state.

**Context to pass:**

```
ticket:               <TICKET>
prompt_path:          $PROMPT_PATH
quality_path:         $QUALITY_PATH
worktree_path:        $WORKTREE_PATH
test_cases_json:      [extracted from Step 1]
agents_md_path:       $WORKTREE_PATH/AGENTS.md
ai_base_rules_path:   ../ai-base-rules/frontend/
e2e_docs_path:        $WORKTREE_PATH/e2e/docs/
e2e_domain_path:      <WORKTREE_PATH>/e2e/tests/<dominio>
e2e_target_specs:     [list of spec files for this ticket]
scope:                "frontend | fullstack" (from PROMPT)
dev_server_port:      [from context]
```

**Dispatch instruction to João:**

> "Você é o João. Sua missão: **escrever TODOS os testes em fase RED (falhando) baseado em QUALITY.md**.
>
> Os testes são a documentação executável do que será implementado. NÃO implemente a funcionalidade ainda.
>
> ### 📋 Tarefa: Escrever Testes para `<TICKET>`
>
> #### Leitura Obrigatória (ANTES de qualquer código):
> 1. ✅ Leia QUALITY.md completamente — este é SEU guia
> 2. ✅ Leia PROMPT.md — entenda o escopo
> 3. ✅ Leia `<WORKTREE_PATH>/AGENTS.md` — fonte de verdade para padrões de teste e desenvolvimento
> 4. ✅ Leia ../ai-base-rules/frontend/05-testing/ — convenções de teste
> 5. ✅ Leia e2e/docs/ — padrões de E2E (Page Object Model, fixtures, etc.)
>
> #### Passo 0: Preparação
> - Suba dev server na porta fornecida (http://localhost:PORT)
> - Verifique se `http://localhost:3001`, `:3002`, `:3003`, `:3004`, `:3005` responde antes de rodar E2E
> - Confirme que `pnpm typecheck` passa
> - Confirme que testes atuais passam (`pnpm test --run`)
>
> #### Passo 1: UNIT TESTS (Vitest + Vue Test Utils)
>
> Para cada TC-XX em QUALITY.md, escreva teste unitário:
>
> **Estrutura obrigatória:**
> - Arquivo: `app/**/__tests__/[component-or-feature].test.ts`
> - Framework: Vitest + Vue Test Utils (conforme AGENTS.md)
> - Padrão: Arrange → Act → Assert
> - Data-testid: Use hashes conforme testid-map.md (se existir)
>
> **Exemplo para TC-01 (TaxRegimeSelect shows required asterisk):**
>
> \`\`\`typescript
> import { describe, it, expect } from 'vitest'
> import { mount } from '@vue/test-utils'
> import TaxRegimeSelect from '~/components/TaxRegimeSelect.vue'
>
> describe('TaxRegimeSelect', () => {
>   it('TC-01: shows required asterisk on label', () => {
>     // ARRANGE
>     const wrapper = mount(TaxRegimeSelect)
>
>     // ACT
>     const label = wrapper.find('label')
>
>     // ASSERT
>     expect(label.text()).toContain('*')
>     // Este teste DEVE FALHAR agora (RED)
>   })
> })
> \`\`\`
>
> **Regras para testes unitários:**
> - ✅ Cada TC = um teste (`it()`)
> - ✅ Testes cobrem: props, events (emit), estado, validação
> - ✅ Use data-testid para seletores (nunca IDs privados)
> - ✅ Moque APIs externas, não a UI
> - ✅ Um teste = uma responsabilidade (AAA pattern)
> - ✅ Nomes descritivos: 'should show error when ... ' não apenas 'error test'
> - ✅ Todos os testes DEVEM FALHAR neste momento (RED state)
>
> #### Passo 2: E2E TESTS (Playwright)
>
> Para cada E2E-XX em QUALITY.md, escreva teste Playwright:
>
> **Estrutura obrigatória:**
> - Arquivo: `<WORKTREE_PATH>/e2e/tests/<dominio>/<flow>.spec.ts`
> - Framework: Playwright (conforme e2e/docs/ARCHITECTURE.md)
> - Padrão: Page Object Model (POM) — use BasePage + page objects
> - Data-testid: Use APENAS hashes da testid-map (encapsulado em POM)
> - Não usar protocolo djalma
>
> **Exemplo para E2E-01 (Save without tax regime — inline error):**
>
> \`\`\`typescript
> import { test, expect } from '@playwright/test'
> import { CustomerEditPage } from '~/e2e/pages'
>
> test.describe('Tax Regime Validation', () => {
>   test('E2E-01: Save without tax regime — shows inline error', async ({ page }) => {
>     // ARRANGE
>     const customerEditPage = new CustomerEditPage(page)
>     await customerEditPage.navigate()
>     await customerEditPage.goToFiscalTab()
>
>     // Ensure tax regime is NOT selected (null)
>     await customerEditPage.clearTaxRegime()
>
>     // ACT
>     await customerEditPage.clickSave()
>
>     // ASSERT
>     expect(await customerEditPage.getTaxRegimeError()).toBe(
>       'Regime Tributário é obrigatório.'
>     )
>     expect(await customerEditPage.hasRedBorder('tax-regime')).toBe(true)
>     expect(await customerEditPage.wasApiCalled()).toBe(false)
>     // Este teste DEVE FALHAR agora (RED)
>   })
> })
> \`\`\`
>
> **Regras para testes E2E:**
> - ✅ Cada E2E-XX = um teste (`test()`)
> - ✅ Use Page Object Model (crie page objects em e2e/pages/ se não existem)
> - ✅ Testes cobrem: navegação, preenchimento, cliques, validações, toasts, redirects
> - ✅ Moque SSO quando necessário (conforme global-setup.ts)
> - ✅ Use data-testid hashes (nunca CSS selectors ou XPath)
> - ✅ Capture screenshots em pontos-chave (para evidência visual)
> - ✅ Todos os testes DEVEM FALHAR neste momento (RED state)
>
> #### Passo 3: REGRESSION TESTS
>
> Para cada item em QUALITY.md \"Regression Checklist\", escreva teste:
> - Valida que feature X não foi quebrada
> - Valida que relacionados ainda funcionam
> - Exemplo: \"Corporate customer edit — all other fiscal tab fields work\"
>
> #### Passo 4: Execute TESTES em modo RED
>
> **Unit tests:**
> \`\`\`bash
> cd $WORKTREE_PATH
> pnpm test -- app/**/__tests__/<feature>.test.ts --run
> # RESULTADO ESPERADO: ❌ TODOS FALHANDO (RED state)
> \`\`\`
>
> **E2E tests:**
> \`\`\`bash
> cd $WORKTREE_PATH
> pnpm e2e:headed -- <WORKTREE_PATH>/e2e/tests/<dominio>/<flow>.spec.ts
> # RESULTADO ESPERADO: ❌ TODOS FALHANDO (RED state)
> \`\`\`
>
> **Capture output:**
> ```bash
> # Salve resultado de testes falhando
> pnpm test -- app/**/__tests__/<feature>.test.ts --run > /tmp/unit-test-red.log 2>&1
> pnpm e2e:headed -- <WORKTREE_PATH>/e2e/tests/<dominio>/<flow>.spec.ts > /tmp/e2e-test-red.log 2>&1
> ```
>
> #### Passo 5: Validação de Completude
>
> Antes de finalizar, valide:
> - ✅ Cada TC em QUALITY.md tem teste unitário correspondente
> - ✅ Cada E2E-XX em QUALITY.md tem teste E2E correspondente
> - ✅ Cada item de \"Regression Checklist\" tem teste
> - ✅ Cada teste ESTÁ FALHANDO (RED state confirmado)
> - ✅ Nenhuma implementação de feature foi feita (apenas testes)
> - ✅ Código de teste segue padrões de AGENTS.md
> - ✅ `pnpm typecheck` passa para testes
>
> #### Passo 6: Retorne Resumo de Testes
>
> Retorne JSON estruturado:
>
> \`\`\`json
> {
>   \"ticket\": \"<TICKET>\",
>   \"tdd_red_complete\": true,
>   \"test_summary\": {
>     \"unit_tests_written\": <number>,
>     \"unit_tests_status\": \"all_failing (RED)\",
>     \"unit_tests_file\": \"<path/to/spec.ts>\",
>     \"e2e_tests_written\": <number>,
>     \"e2e_tests_status\": \"all_failing (RED)\",
>     \"e2e_tests_file\": \"<path/to/e2e.spec.ts>\",
>     \"regression_tests_written\": <number>
>   },
>   \"test_artifacts\": {
>     \"unit_test_log\": \"[output snippet]\",
>     \"e2e_test_log\": \"[output snippet]\"
>   },
>   \"e2e_domain_path\": \"<WORKTREE_PATH>/e2e/tests/<dominio>\",
>   \"e2e_target_specs\": [\"<WORKTREE_PATH>/e2e/tests/<dominio>/<flow>.spec.ts\"],
>   \"next_phase\": \"/execute-transition -> /execute-implementation\",
>   \"quality_md_coverage\": \"100%\"
> }
> \`\`\`
>
> #### 🚨 Safety Rules
> - **WRITE TESTS ONLY** — não implemente nada da funcionalidade
> - **RED STATE MANDATORY** — todos os testes devem falhar
> - **QUALITY.MD IS SOURCE OF TRUTH** — cada test case em QUALITY.md deve ter teste correspondente
> - **AGENTS.MD COMPLIANCE** — siga padrões de teste do projeto
> - **DATA-TESTID** — use sempre (nunca invented selectors)
> - **No Mock Cheating** — não moque o que deveria ser testado
> - **E2E HEADED ONLY** — para E2E use sempre modo headed
> - **KEYCLOAK RULE** — se houver redirecionamento para Keycloak, pause e solicite autenticação manual do usuário
> - **NO DJALMA** — protocolo djalma é proibido; usar apenas automações em `<WORKTREE_PATH>/e2e/tests/<dominio>`
>
> **Modo: `/execute-tdd-red` — você está escrevendo testes, NÃO implementação.**
> **Próximo passo será `/execute-transition` (status) e depois `/execute-implementation` para passar nesses testes.**"

**Wait for João's test summary JSON.**

---

## Step 3 — Analyze Test Results

Parse João's test_summary:

```json
{
  "tdd_red_complete": true,
  "test_summary": {
    "unit_tests_written": <number>,
    "unit_tests_status": "all_failing (RED)",
    "e2e_tests_written": <number>,
    "e2e_tests_status": "all_failing (RED)",
    "regression_tests_written": <number>
  },
  "quality_md_coverage": "100%"
}
```

### Validation Matrix:

| Check | Expected | Action |
|-------|----------|--------|
| `tdd_red_complete` | `true` | ✅ Proceed |
| `unit_tests_status` | "all_failing (RED)" | ✅ Correct |
| `e2e_tests_status` | "all_failing (RED)" | ✅ Correct |
| `quality_md_coverage` | "100%" | ✅ Full coverage |
| Any tests passing | None | ⛔ Red phase violation |

If validation fails:
> "⚠️ TDD-RED validation failed:
> - Status: <actual_status>
> - Expected: all_failing
> - Action: João deve revisar e garantir que TODOS os testes estão falhando"

**Ask for clarification before proceeding.**

---

## Step 4 — Verify Test File Structure

Verify that test files are properly committed to worktree:

```bash
cd $WORKTREE_PATH
find app e2e/tests -type f \( -name "*.test.ts" -o -name "*.spec.ts" \) | head -20
```

Expected structure:
```
app/**/__tests__/
  ├── <feature>.test.ts
  └── <feature>.spec.ts (when repository pattern uses .spec)

e2e/tests/
  ├── <dominio>/
  │   └── <flow>.spec.ts
```

If structure is wrong:
> "⚠️ Estrutura de testes não segue padrões:
> - Esperado: app/**/__tests__/<feature>.test.ts, <WORKTREE_PATH>/e2e/tests/<dominio>/<flow>.spec.ts
> - Encontrado: <actual>
> - Corrija antes de prosseguir"

---

## ✅ SUCCESS PATH

Return result:
```json
{
  "ticket": "<TICKET>",
  "tdd_red_passed": true,
  "unit_tests_count": <number>,
  "e2e_tests_count": <number>,
  "regression_tests_count": <number>,
  "total_tests": <number>,
  "test_files_created": [<paths>],
  "all_tests_failing": true,
  "quality_md_coverage": "100%",
  "ready_for_implementation": true
}
```

**Proceed to next phase: `/execute-transition` (status) -> `/execute-implementation`**

---

## 🚫 FAILURE PATH

If tests are not all failing or QUALITY.md coverage incomplete:

> "❌ TDD-RED validation failed:
> - Testes passando: <count> (deveria ser 0)
> - QUALITY.md coverage: <coverage>% (deveria ser 100%)
>
> João deve:
> 1. Revisar testes — garantir que FALHAM
> 2. Completar cobertura de QUALITY.md
> 3. Não implementar — apenas escrever testes"

**Stop. Do not proceed to implementation phase until RED state is confirmed.**

---

## Safety Rules

- **RED state is mandatory** — all tests must fail before proceeding
- **No implementation** — this phase ONLY writes tests
- **QUALITY.md is source of truth** — 100% of test cases must have tests
- **AGENTS.md compliance** — tests follow project patterns
- **AGENTS as source-of-truth** — em caso de conflito, siga `<WORKTREE_PATH>/AGENTS.md`
- **Data-testid mandatory** — never use invented selectors in tests
- **Test coverage** — regression checklist must be included
- **Test documentation** — each test should be self-documenting (clear names, good assertions)
- If João reports issues → stop and ask for fixes before continuing
- Never proceed to implementation without confirmed RED state
