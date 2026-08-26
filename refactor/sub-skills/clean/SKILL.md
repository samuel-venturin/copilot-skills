---
name: refactor-clean
description: Clean Code sub-skill - Applies SOLID principles and clean code best practices.
---

# Clean Sub-Skill: Clean Code

Applies SOLID principles and clean code best practices to improve code quality and maintainability.

## What This Sub-Skill Does

- Identifies overly long functions (>50 lines)
- Detects high cyclomatic complexity
- Finds duplicate code (DRY violations)
- Identifies functions with side effects
- Detects magic numbers without explanation
- Suggests refactoring to apply SOLID principles

## SOLID Principles

### Single Responsibility Principle (SRP)
Each function/class should have ONE reason to change

```javascript
// ❌ BEFORE: Multiple responsibilities
function saveUserAndSendEmail(user) {
  // Validate
  if (!user.email) throw new Error();
  // Save to database
  database.save(user);
  // Send email
  sendEmail(user.email, 'Welcome!');
  // Log
  logger.info('User saved');
}

// ✅ AFTER: Separated concerns
function saveUser(user) {
  validateUser(user);
  return database.save(user);
}

function onUserCreated(user) {
  sendWelcomeEmail(user);
  logUserCreation(user);
}
```

### Open/Closed Principle (OCP)
Open for extension, closed for modification

### Liskov Substitution Principle (LSP)
Subtypes must be substitutable for base types

### Interface Segregation Principle (ISP)
Many client-specific interfaces better than one general-purpose

### Dependency Inversion Principle (DIP)
Depend on abstractions, not concrete implementations

## Common Issues

### 1. Long Functions
```javascript
// ❌ BEFORE: 120 lines
function processCustomerOrder(customer, items) {
  // Validation (20 lines)
  // Calculation (30 lines)
  // Payment processing (25 lines)
  // Inventory update (20 lines)
  // Email notification (25 lines)
}

// ✅ AFTER: Broken into focused functions
async function processCustomerOrder(customer, items) {
  validateOrder(customer, items);
  const total = calculateOrderTotal(items);
  await processPayment(customer, total);
  await updateInventory(items);
  await sendOrderConfirmation(customer);
}
```

### 2. Code Duplication (DRY)
```javascript
// ❌ BEFORE: Repeated validation
function validateEmail(email) {
  if (!email.includes('@')) throw new Error('Invalid');
  if (email.length < 5) throw new Error('Too short');
}

function validatePassword(password) {
  if (!password.includes('@')) throw new Error('Invalid');
  if (password.length < 5) throw new Error('Too short');
}

// ✅ AFTER: Shared validator
function validateFormat(value, pattern, minLength) {
  if (!value.includes(pattern)) throw new Error('Invalid');
  if (value.length < minLength) throw new Error('Too short');
}

const validateEmail = (email) => validateFormat(email, '@', 5);
const validatePassword = (pwd) => validateFormat(pwd, '@', 5);
```

### 3. Side Effects
```javascript
// ❌ BEFORE: Mixed concerns
function calculateTotal(items) {
  const total = items.reduce((sum, item) => sum + item.price, 0);
  console.log('Total:', total);           // Side effect
  localStorage.setItem('lastTotal', total); // Side effect
  analyticsAPI.track('order_total', total); // Side effect
  return total;
}

// ✅ AFTER: Pure function + separate handlers
function calculateTotal(items) {
  return items.reduce((sum, item) => sum + item.price, 0);
}

function onOrderComplete(total) {
  console.log('Total:', total);
  localStorage.setItem('lastTotal', total);
  analyticsAPI.track('order_total', total);
}
```

### 4. Magic Numbers
```javascript
// ❌ BEFORE
function calculateDiscount(price) {
  return price > 100 ? price * 0.15 : price * 0.05; // Magic numbers!
}

// ✅ AFTER
const PREMIUM_THRESHOLD = 100;
const PREMIUM_DISCOUNT_RATE = 0.15;
const STANDARD_DISCOUNT_RATE = 0.05;

function calculateDiscount(price) {
  const discountRate = price > PREMIUM_THRESHOLD
    ? PREMIUM_DISCOUNT_RATE
    : STANDARD_DISCOUNT_RATE;
  return price * discountRate;
}
```

## Output Format

```markdown
---
feature: customer
arquivo: app/pages/customer/edit.vue
tipo: CLEAN (Clean Code)
arquivos_relacionados: none
porque: Aplicar princípios SOLID e reduzir complexidade
---

# customer-edit-clean.spec

## Melhorias identificadas
- Função `handleFormSubmit` com 87 linhas (linha 234)
- Código duplicado: validação repetida 3x (linhas 156, 178, 201)
- Números mágicos: 100, 0.15, 0.05 sem contexto (linhas 267-270)
- Função mista: salva + envia email + loga (linha 145)

## Por que mudar
- Reduz complexidade cognitiva
- Facilita testes unitários
- Melhora manutenibilidade
- Aplica SOLID principles

## Como
1. Quebrar `handleFormSubmit` em 3-4 funções focadas
2. Extrair validação para função reutilizável
3. Definir constantes para valores mágicos
4. Separar salvar de notificações

## Onde
- Linhas 234-321, 156, 178, 201, 267-270, 145

## O que
[Código refaturado com funções menores e mais focadas]
```
