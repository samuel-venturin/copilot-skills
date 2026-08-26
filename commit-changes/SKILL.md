---
name: commit-changes
description: Commit changes using atomic commits following ScanSource Brazil commit convention. Runs required checks, stages selectively, and creates well-formed commits. Never pushes automatically.
---

# Commit Changes Skill

## Padrão de commit — ScanSource Brazil (global, vale para todos os projetos)

```
[TICKET][TYPE]: description
```

### Tipos válidos

| Tipo | Quando usar |
|------|-------------|
| `[FEAT]` | Nova funcionalidade |
| `[FIX]` | Correção de bug |
| `[REFAC]` | Refatoração sem mudança de comportamento |
| `[DOCS]` | Documentação |
| `[STYLE]` | Formatação, espaçamento (sem impacto funcional) |
| `[TEST]` | Adição ou modificação de testes |
| `[BUILD]` | Build system, dependências externas |
| `[CI]` | Configuração de CI/CD |
| `[CHORE]` | Tarefas de manutenção (sem impacto em src/test) |
| `[PERF]` | Melhorias de performance |
| `[REVERT]` | Reversão de commit anterior |

### Regras obrigatórias

- **TICKET:** extrair do nome da branch (ex: `fix/CTR-624` → `CTR624`)
- **TYPE:** sempre UPPERCASE
- **description:** imperativo, conciso, sem ponto final
- **Header:** máximo 100 caracteres (ticket + tipo + descrição)
- **Idioma:** sempre inglês, mesmo que o código esteja em outro idioma
- **Body:** sempre adicionar body com detalhes das mudanças (conciso)

### Exemplos

```bash
git commit -m "[CTR624][FEAT]: add tax exemption filter to customer list"
git commit -m "[CTR624][FIX]: resolve pagination reset on filter change"
git commit -m "[CTR624][REFAC]: extract useCustomerRepo composable from store"
git commit -m "[CTR624][DOCS]: update AGENTS.md with task-executor skill"

# Com body
git commit -m "[CTR624][FEAT]: add UX context gate to task interpreter" \
           -m "- Add UX_CONTEXT_GATE to interpret flow (step 4)
- Dispatch se-ux-ui-designer when screen docs are missing
- Capture aria-snapshot and screenshots at 3 viewports
- Delete snapshots after docs are written
- Pass ux_context_paths to PM_PRD_GATE"
```

---

## Fluxo de execução

### 1. Inspecionar estado do repositório

```bash
git status -sb
git diff
```

- Identificar arquivos modificados e novos
- Se aparecer algo fora do escopo acordado → **alinhar com o usuário antes de continuar**
- Nunca reverter mudanças do usuário sem confirmação explícita

### 2. Determinar ticket

```bash
git branch --show-current
```

- Extrair ticket do nome da branch: `fix/CTR-624` → `CTR624`, `us/CTR-1135` → `CTR1135`
- Se branch não tem ticket (ex: `develop`, `main`) → usar `[CHORE]` sem ticket: `[CHORE]: description`

### 3. Rodar verificações obrigatórias

Adaptar ao projeto. Para projetos **frontend (pnpm)**:
```bash
pnpm typecheck
pnpm test --run
```

Para projetos **backend (.NET)**:
```bash
dotnet build
dotnet test
```

> ⛔ Não continuar se qualquer verificação falhar. Reportar o erro ao usuário.

### 4. Decidir: um ou múltiplos commits?

Avaliar se as mudanças têm **temas lógicos distintos**:
- Mesmo tema → um commit atômico
- Temas distintos → múltiplos commits, um por tema

Exemplos de split:
```bash
# Errado — mistura de preocupações
git commit -m "[CTR624][FEAT]: add filter and fix pagination bug"

# Correto — commits separados
git commit -m "[CTR624][FEAT]: add customer status filter"
git commit -m "[CTR624][FIX]: resolve pagination reset on filter change"
```

### 5. Preparar staging area

```bash
git add <path/to/file>   # nunca usar git add .
git diff --cached        # verificar o que foi staged
```

- Adicionar apenas arquivos do escopo do commit
- Verificar staged diff antes de continuar

### 6. Criar o commit

```bash
git commit -m "[TICKET][TYPE]: description" -m "<body>"
```

- Sempre incluir body descrevendo o que foi feito
- Se mais de um tema lógico: repetir steps 5–6 para cada tema

### 7. Verificar estado final

```bash
git status -sb
```

- Confirmar que não há mudanças pendentes do escopo commitado

---

## Post-commit

- Reportar o hash do commit criado + resumo das mudanças
- Lembrar que o push é **manual** — nunca fazer push automaticamente
- Se qualquer step falhar → parar e reportar o erro imediatamente

---

## Commits desta sessão (quando não há ticket de branch)

Para commits de configuração/agentes/skills fora de uma task:
```bash
git commit -m "[CHORE]: <description>"
```

Exemplos:
```bash
git commit -m "[CHORE]: add task-executor skill and Caio tech lead agent"
git commit -m "[CHORE]: globalize commit-changes and update AGENTS.md"
```
