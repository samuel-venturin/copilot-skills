---
name: refactor-rdc
description: Remove Dead Code sub-skill - Identifies and removes unused functions, variables, imports, and dead code paths.
---

# RDC Sub-Skill: Remove Dead Code

Identifies and removes unused functions, variables, imports, and dead code paths to improve code quality and reduce complexity.

## What This Sub-Skill Does

- Detects unused function definitions
- Identifies unused variable declarations
- Finds unused imports and dependencies
- Locates dead code paths (unreachable code)
- Suggests safe removal strategies

## Typical Issues Found

```javascript
// Unused function
function calculateOldFormula() {  // ❌ Never called
  return x * y;
}

// Unused variable
const tempData = fetchData();     // ❌ Declared but never used
console.log('Processing...');

// Unused import
import { helper } from './utils'; // ❌ Not referenced

// Dead code path
if (condition) {
  doSomething();
} else if (false) {               // ❌ Unreachable
  unreachableFunction();
}
```

## How It Works

1. **Analysis Phase**: Scans code for unused declarations and references
2. **Spec Generation**: Creates detailed removal guidance with line numbers
3. **User Review**: Shows what will be removed and why
4. **Application**: Removes dead code with confirmation

## Safety

- Never removes code that might be referenced dynamically
- Preserves public APIs and exports
- Skips names starting with `_` (intentionally unused)
- Requires explicit user confirmation before changes

## Typical Output

```markdown
---
feature: customer
arquivo: app/pages/customer/list.vue
tipo: RDC (Remove Dead Code)
arquivos_relacionados: none
porque: Reduz complexidade e melhora manutenibilidade
---

# customer-list-rdc.spec

## Melhorias identificadas
- Função `handleOldFiltering` nunca é chamada (linha 234)
- Variável `unused_temp` declarada mas não utilizada (linha 156)
- Import de `helperFn` não é usado (linha 12)

## Por que mudar
- Reduz complexidade cognitiva
- Melhora legibilidade
- Facilita manutenção futura

## Como
1. Remove função inteira (34 linhas)
2. Remove declaração de variável
3. Remove import não utilizado

## Onde
- Linhas 234-268 (função)
- Linha 156 (variável)
- Linha 12 (import)

## O que
[Código será removido completamente]
```
