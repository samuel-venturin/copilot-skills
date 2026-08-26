---
name: refactor-naming
description: Naming Conventions sub-skill - Standardizes variable, function, and class naming for consistency and clarity.
---

# Naming Sub-Skill: Naming Conventions

Standardizes variable, function, and class naming to improve code consistency and clarity.

## What This Sub-Skill Does

- Identifies single-letter or unclear variable names
- Detects inconsistent naming conventions
- Finds excessive abbreviations
- Suggests descriptive alternatives
- Standardizes camelCase vs snake_case conventions

## Naming Standards

### JavaScript/TypeScript/Vue
- **Variables & Functions**: `camelCase`
- **Classes**: `PascalCase`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Private methods**: `_leadingUnderscore`
- **Booleans**: prefix with `is`, `has`, `can`, `should`

### Avoid
- Single-letter names (except loop counters: `i`, `j`, `k`)
- Abbreviations (`desc`, `fn`, `mgr`, `num`)
- Temporary names (`temp`, `tmp`, `data`)
- Vague names (`value`, `item`, `thing`)

## Typical Issues Found

```javascript
// ❌ Single letter
const x = calculateValue();
const arr = [];
let y = 0;

// ❌ Abbreviations
const desc = getDescription();
const mgr = getUserManager();
const info = {};

// ❌ Vague names
const temp = processData();
const value = getData();
const thing = transform(input);

// ❌ Inconsistent casing (mixing styles)
const user_name = 'John';    // snake_case in JS
const userEmail = 'john@...'; // camelCase
```

## Naming Guidelines

```javascript
// ✅ Descriptive and consistent
const firstName = 'John';
const emailAddress = 'john@example.com';
const isActive = true;
const canDelete = userRole === 'admin';
const userManager = new UserManager();
const API_KEY = process.env.API_KEY;

// ✅ Functions should describe actions
function validateEmail(email) { ... }
function fetchUserData(userId) { ... }
function handleFormSubmit(event) { ... }
function isUserPermitted(user, action) { ... }

// ✅ Event handlers
function onSubmit() { ... }
function onClick() { ... }
function onUserUpdate() { ... }
```

## Output Format

```markdown
---
feature: customer
arquivo: app/components/CustomerForm.vue
tipo: naming (Naming Conventions)
arquivos_relacionados: none
porque: Padroniza e melhora legibilidade do código
---

# customer-form-naming.spec

## Melhorias identificadas
- Variável `x` deve ser `customerData` (linha 45)
- Abreviação `desc` deve ser `description` (linha 78)
- Nome vago `temp` deve ser `processedCustomer` (linha 92)
- snake_case `user_email` deve ser `userEmail` (linha 156)

## Por que mudar
- Melhora consistência
- Aumenta legibilidade
- Facilita busca e refatoração

## Como
Renomear variáveis preservando todas as referências

## Onde
- Linhas 45, 78, 92, 156

## O que
- x → customerData
- desc → description
- temp → processedCustomer
- user_email → userEmail
```
