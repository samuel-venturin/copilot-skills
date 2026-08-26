---
name: execute-code-review
description: Rigorous code review against DRY, SOLID, FUNCTIONAL PROGRAMMING, CLEAN CODE, and project standards (AGENTS.md). Runs after implementation and before QA validation.
---

# /execute-code-review — Code Review Phase

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`

Input (from `/execute-implementation` output):
- `$TICKET` — task ID
- `$WORKTREE_PATH` — worktree where code was executed
- `$EXECUTION_SUMMARY` — Caio's execution results

---

## Overview

This phase performs **rigorous, multi-dimensional code quality validation** on all changes made during execution. It is **foreground-only** and must complete before user approval.

**Validation dimensions:**
1. **DRY** (Don't Repeat Yourself) — No code duplication
2. **SOLID Principles** — Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion
3. **Functional Programming** — Pure functions, immutability, function composition where applicable
4. **Clean Code** — Readability, naming, complexity, testability
5. **Project Standards** — follow `<WORKTREE_PATH>/AGENTS.md` as source of truth for project conventions

---

## Step 6.1 — Collect Changed Files

```bash
cd $WORKTREE_PATH
git diff origin/develop --name-only
```

Store the list of modified files by type:
- Frontend files (*.ts, *.tsx, *.vue, *.js, *.jsx)
- Backend files (*.cs, *.py, etc.)
- Tests (*.test.ts, *.test.cs, etc.)
- Other (config, docs, etc.)

If **no code changes** detected:
> "⚠️ Nenhuma alteração de código detectada. Worktree pode não ter mudanças ou branch está sincronizado com origin/develop.
> Deseja continuar para aprovação assim mesmo? (sim/não)"

If user says no → STOP and ask what went wrong.

---

## Step 6.2 — Dispatch Caio for Quality Review

Build context and dispatch Caio (Tech Lead) **specifically for code review**. This is a **different mindset** from execution — now Caio acts as a strict code reviewer.

**Context to pass:**

```
ticket:               <TICKET>
worktree_path:        <WORKTREE_PATH>
changed_files:        [list from Step 6.1]
execution_summary:    <Caio's previous execution_summary>
code_standards_path:  ~/.copilot/docs/code-standards.md
agents_md_path:       <WORKTREE_PATH>/AGENTS.md
atena_ui_path:        ../atena-ui
```

**Dispatch instruction to Caio:**

> "Você é o Caio em modo **CODE QUALITY REVIEWER**. Sua missão é validar RIGOROSAMENTE o código alterado em `<TICKET>`.
>
> **CRÍTICO: Você DEVE ler TODOS os arquivos alterados e executar análise multi-dimensional:**
>
> ### Dimensão 1: DRY (Don't Repeat Yourself)
> - Procure por duplicação de código, lógica repetida, padrões que poderiam ser abstratos
> - Verifique se há oportunidades de consolidar em funções/utilitários reutilizáveis
> - Marque violações com severidade: CRÍTICA | ALTA | MÉDIA | BAIXA
>
> ### Dimensão 2: SOLID Principles
> - **S**ingle Responsibility: Cada função/classe tem UMA responsabilidade?
> - **O**pen/Closed: Código aberto para extensão, fechado para modificação?
> - **L**iskov Substitution: Subtypes são substituíveis sem quebrar lógica?
> - **I**nterface Segregation: Interfaces específicas, não genéricas demais?
> - **D**ependency Inversion: Dependências injetadas, não hardcoded?
> - Marque violações com severidade: CRÍTICA | ALTA | MÉDIA | BAIXA
>
> ### Dimensão 3: Functional Programming
> - Funções são puras (sem side effects)? Se não, é documentado?
> - Dados são imutáveis onde possível?
> - Há composição de funções em vez de lógica complexa aninhada?
> - Marque violações com severidade: CRÍTICA | ALTA | MÉDIA | BAIXA
>
> ### Dimensão 4: Clean Code
> - Nomes de variáveis, funções, classes são claros e intencionais?
> - Funções têm complexidade razoável (não mais de 20 linhas)?
> - Há comentários quando necessário (lógica não-óbvia)?
> - Código é testável?
> - Marque violações com severidade: CRÍTICA | ALTA | MÉDIA | BAIXA
>
> ### Dimensão 5: Project Standards (`<WORKTREE_PATH>/AGENTS.md` + code-standards.md)
> - Segue convenções de commit?
> - Respeita arquitetura em camadas (routes/handlers/services/repositories)?
> - Usa padrões de erro tipados?
> - Segue SOLID obrigatório?
> - Padrões de teste (TDD, cobertura)?
> - Marque violações com severidade: CRÍTICA | ALTA | MÉDIA | BAIXA
> - Em caso de conflito com regras gerais, prevalece `<WORKTREE_PATH>/AGENTS.md`
>
> ---
>
> **RETORNE um relatório JSON estruturado:**
>
> \`\`\`json
> {
>   \"ticket\": \"<TICKET>\",
>   \"code_review\": {
>     \"total_files_reviewed\": <number>,
>     \"violations\": [
>       {
>         \"file\": \"<file_path>\",
>         \"line\": <line_number>,
>         \"dimension\": \"DRY | SOLID | FP | CLEAN_CODE | PROJECT_STANDARDS\",
>         \"severity\": \"CRÍTICA | ALTA | MÉDIA | BAIXA\",
>         \"description\": \"<what's wrong>\",
>         \"suggestion\": \"<how to fix it>\",
>         \"code_snippet\": \"<current code (max 5 lines)>\"
>       }
>     ],
>     \"quality_score\": {
>       \"dry\": <0-100>,
>       \"solid\": <0-100>,
>       \"functional_programming\": <0-100>,
>       \"clean_code\": <0-100>,
>       \"project_standards\": <0-100>,
>       \"overall\": <0-100>
>     },
>     \"critical_violations_count\": <number>,
>     \"high_violations_count\": <number>
>   },
>   \"recommendation\": \"APPROVED | NEEDS_IMPROVEMENT | REJECTED\",
>   \"next_steps\": \"<action required if not approved>\"
> }
> \`\`\`
>
> **REGRA DE DECISÃO:**
>
> - Se **0 CRÍTICA** e **≤2 ALTA**: Recomenda APPROVED (sugestões podem ser implementadas depois)
> - Se **1-2 CRÍTICA** ou **3+ ALTA**: Recomenda NEEDS_IMPROVEMENT (Caio deve propor fix e reexecuta)
> - Se **3+ CRÍTICA**: Recomenda REJECTED (bloqueia approve, exige retrabalho)
>
> **Se NEEDS_IMPROVEMENT ou REJECTED:**
> - Descreva as mudanças necessárias de forma clara e priorizada
> - Indique se você já começou a corrigir ou se o engenheiro deve fazer
> - Peça confirmação do usuário antes de qualquer reexecução"

**Wait for Caio's code review JSON.**

---

## Step 6.3 — Analyze Review Results

Parse Caio's code_review JSON:

```json
{
  "recommendation": "APPROVED | NEEDS_IMPROVEMENT | REJECTED",
  "critical_violations_count": <number>,
  "high_violations_count": <number>,
  "code_review_score": { ... },
  "violations": [ ... ]
}
```

### Decision Matrix:

| Recommendation | Action | Next Step |
|---|---|---|
| **APPROVED** | ✅ Quality passed | Proceed to `/execute-qa-validation` |
| **NEEDS_IMPROVEMENT** | ⚠️ Issues found, fixable | Show violations, ask user (a) Auto-fix / (b) Manual fix / (c) Override |
| **REJECTED** | ❌ Blocker found | Stop, escalate, do not proceed to approve |

---

## Step 6.4 — Handle APPROVED

If `recommendation = APPROVED`:

Display summary:
```
✅ Validação de qualidade APROVADA — <TICKET>

Quality Score:
  DRY:                    <score>/100
  SOLID:                  <score>/100
  Functional Programming: <score>/100
  Clean Code:             <score>/100
  Project Standards:      <score>/100
  ─────────────────────────
  OVERALL:                <overall_score>/100

Violações por severidade:
  🔴 Crítica:  <count>
  🟠 Alta:     <count>
  🟡 Média:    <count>
  🟢 Baixa:    <count>

Próximo passo: Ir para aprovação final
```

**Return success:**
```json
{
  "ticket": "<TICKET>",
  "code_review_passed": true,
  "recommendation": "APPROVED",
  "overall_code_review_score": <score>,
  "violations_summary": { ... }
}
```

**Proceed to `/execute-qa-validation`**

---

## Step 6.5 — Handle NEEDS_IMPROVEMENT

If `recommendation = NEEDS_IMPROVEMENT`:

1. Display all violations categorized by dimension:
```
⚠️ Validação de Qualidade — MELHORIAS NECESSÁRIAS — <TICKET>

Quality Score: <overall_score>/100

Violações encontradas:

[DRY]
  🔴 CRÍTICA | file.ts:42 — Duplicação de parseUserData()
     Sugestão: Mover para utils/userParsers.ts
     
  🟠 ALTA | file.ts:87 — Lógica de validação repetida 3x
     Sugestão: Extrair em função validate()

[SOLID]
  🟠 ALTA | handler.ts:15 — Violação SRP: handler faz 3 coisas
     Sugestão: Separar em service + repository

... (mais violações)

Recomendação: NEEDS_IMPROVEMENT
```

2. Ask user:
> "(a) Deixar Caio corrigir automaticamente (se possível)
> (b) Você quer corrigir manualmente — pause para você editar
> (c) Aceitar risco e prosseguir para aprovação mesmo assim"

3. **If (a):** Ask Caio to apply fixes, re-run code review, loop back to Step 6.3
4. **If (b):** Pause, wait for user to edit, then re-run `/execute-code-review` with updated worktree
5. **If (c):** Log override, but still proceed to `/execute-qa-validation` (user takes responsibility)

---

## Step 6.6 — Handle REJECTED

If `recommendation = REJECTED`:

Display critical violations:
```
❌ Validação de Qualidade — REJEITADA — <TICKET>

Quality Score: <overall_score>/100

🔴 VIOLAÇÕES CRÍTICAS (bloqueiam aprovação):

[SOLID]
  🔴 CRÍTICA | service.ts:30 — Dependency Inversion violada: hardcoded database import
     Sugestão: Injetar repository via construtor
     
  🔴 CRÍTICA | handler.ts:45 — Single Responsibility violada: handler faz SQL + validação + formatação
     Sugestão: Separar em service layers (validate → query → format)

[PROJECT_STANDARDS]
  🔴 CRÍTICA | api.ts:12 — Sem tratamento de erro tipado
     Sugestão: Usar DomainError com ErrorCode typed

Recomendação: REJECTED — Bloqueador encontrado. Não é possível prosseguir para aprovação.

Ações necessárias:
1. Corrija as violações críticas acima
2. Reexecute Caio para reimplementar com os padrões corretos
3. Reexecute /execute-code-review para revalidar
```

**Stop. Do not proceed to `/execute-qa-validation`.**

Return failure:
```json
{
  "ticket": "<TICKET>",
  "code_review_passed": false,
  "recommendation": "REJECTED",
  "overall_code_review_score": <score>,
  "critical_violations": [ ... ],
  "blocking_reason": "Violações críticas detectadas que violam projeto standards obrigatórios"
}
```

---

## ✅ SUCCESS PATH

Return result:
```json
{
  "ticket": "<TICKET>",
  "code_review_passed": true,
  "recommendation": "APPROVED | NEEDS_IMPROVEMENT (with override)",
  "overall_code_review_score": <0-100>,
  "violations_total": <count>,
  "critical_violations": <count>
}
```

**Proceed to next phase: `/execute-qa-validation`**

---

## Safety Rules

- **Foreground-only** — never run code review in background
- Never skip code review before user approval
- REJECTED blocks approval completely — user must fix and rerun
- NEEDS_IMPROVEMENT with override is tracked (user responsibility)
- Quality scores are informational; decisions are based on violations count + severity
- If Caio is unavailable → stop and inform user
- Never weaken quality standards to force approval
