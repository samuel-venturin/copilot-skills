---
name: refactor-se
description: Simplify Expressions sub-skill - Reduces complexity and improves readability of conditional logic and expressions.
---

# SE Sub-Skill: Simplify Expressions

Reduces complexity and improves readability of conditional logic, method chains, and expressions.

## What This Sub-Skill Does

- Detects nested ternary operators
- Identifies overly complex conditional expressions
- Finds long method chains without intermediate variables
- Suggests refactoring to extract variables or helper functions
- Improves code readability through simplification

## Typical Issues Found

```javascript
// ❌ Nested ternaries
const status = user.isActive ? (user.isPremium ? 'premium' : 'active') : 'inactive';

// ❌ Complex conditionals
if ((user.role === 'admin' || user.role === 'moderator') &&
    (data.status === 'pending' || data.status === 'review') &&
    !data.archived) {
  process();
}

// ❌ Long chains
result = collection
  .filter(x => x.valid)
  .map(x => x.transform())
  .reduce((a, b) => a + b, 0)
  .toString()
  .split(',')
  .map(s => s.trim())
  .join('-');
```

## How It Works

1. **Analysis**: Detects complex expressions using heuristics
2. **Spec Generation**: Suggests simplification strategies
3. **User Review**: Shows before/after patterns
4. **Application**: Applies refactoring with confirmation

## Simplification Strategies

### For Nested Ternaries
```javascript
// ❌ BEFORE
const status = isActive ? (isPremium ? 'premium' : 'active') : 'inactive';

// ✅ AFTER
const getStatus = (isActive, isPremium) => {
  if (!isActive) return 'inactive';
  return isPremium ? 'premium' : 'active';
};
const status = getStatus(isActive, isPremium);
```

### For Complex Conditions
```javascript
// ❌ BEFORE
if ((user.role === 'admin' || user.role === 'moderator') &&
    (data.status === 'pending' || data.status === 'review')) {
  process();
}

// ✅ AFTER
const isModeratorOrAdmin = user.role === 'admin' || user.role === 'moderator';
const isPendingOrReview = data.status === 'pending' || data.status === 'review';

if (isModeratorOrAdmin && isPendingOrReview) {
  process();
}
```

## Output Format

```markdown
---
feature: customer
arquivo: app/components/CustomerForm.vue
tipo: SE (Simplify Expressions)
arquivos_relacionados: none
porque: Melhora legibilidade e reduz complexidade cognitiva
---

# customer-form-se.spec

## Melhorias identificadas
- Operador ternário aninhado (linha 89)
- Cadeia de método muito longa (linhas 145-152)
- Condicional com 4+ condições (linha 234)

## Por que mudar
- Aumenta legibilidade
- Reduz complexidade cognitiva
- Facilita testes e manutenção

## Como
1. Extrair condição para variável nomeada
2. Quebrar método chain em variáveis intermediárias
3. Converter ternário para if/else

## Onde
- Linhas 89, 145-152, 234

## O que
[Versão simplificada com variáveis intermediárias]
```
