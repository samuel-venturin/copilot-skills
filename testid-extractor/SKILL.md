---
name: testid-extractor
description: Extract data-testid from pages using testid-v2 plugin. Self-contained skill that handles authentication internally using e2e/auth module. Captures dynamically generated hashes and creates docs/testid-map.md for reference in E2E tests and pattern validation.
---

# TestID Extractor Skill

Extrai `data-testid` attributes gerados pelo plugin `testid-v2` das páginas da aplicação e cria um mapa de referência.

## What This Skill Does

- **Lida com autenticação internamente** — Chama `e2e/auth` module para validar/renovar sessão
- **Valida cookies** — Se expirados, realiza login SSO automático
- **Atualiza `.env.e2e`** — Salva cookies frescos para próximas execuções
- **Navega até cada rota** configurada em `config.json`
- **Aguarda hidratação Vue** (waitForSelector `[data-testid]`)
- **Captura todos os `data-testid`** com categorização por padrão
- **Mapeia padrões** de hash FNV-1a
- **Gera `.testid-extraction.json`** pronto para Pattern Analyzer

### Key Improvements (After Redesign)

| Aspecto | Manual Script | Self-Contained Skill |
|---------|---------------|----------------------|
| **Autenticação** | Manual: `pnpm e2e:headed` | Automática via `e2e/auth` |
| **Cookies** | Depende de cookies válidos | Valida/renova automaticamente |
| **Configuração** | `BASE_URL=...` env var | Sem configuração necessária |
| **Speed** | ~30s/página | ~1-2s/página |
| **Browser** | Headed (com vídeo) | Headless (nenhuma UI) |
| **Output** | Assertions | JSON estruturado |
| **Prerequisites** | Sim (rodar testes primeiro) | Não (totalmente independente) |

## Setup

### Requirements

- Development server running: `pnpm dev`
- Valid credentials in `e2e/.env.e2e` (E2E_USER_EMAIL, E2E_USER_PASSWORD)

That's it! No manual cookie generation needed.

## Invocation

```bash
# Extract testids from all configured pages
/testid-extractor

# The skill handles everything:
# 1. Checks if server is running
# 2. Validates session (reads cookies from .env.e2e)
# 3. If cookies expired: performs SSO login and updates .env.e2e
# 4. Extracts testids from all routes
# 5. Generates docs/testid-map.md and .testid-extraction.json
```

## How It Works

### Architecture: Self-Contained with Internal Auth

```
/testid-extractor
    ↓
Python Script (testid_extractor.py)
  └─ Cria Node.js script
    ↓
Node.js Script (.testid-extractor.mjs)
  └─ Importa e2e/auth module
  └─ Chama getAuthenticatedContext() {
      ├─ Injeta cookies de .env.e2e
      ├─ Valida sessão (GET /customer/list + waitForSelector)
      ├─ Se válida: usa cookies existentes
      ├─ Se expirada: realiza SSO login
      ├─ Atualiza .env.e2e com cookies frescos
      └─ Retorna contexto autenticado
    }
  └─ Para cada rota:
      └─ Reutiliza mesma página (FAST!)
      └─ page.goto(/route)
      └─ Aguarda [data-testid]
      └─ Extrai testids do DOM
      └─ Categoriza por padrão
    ↓
Salva: .testid-extraction.json com resultado completo
```

### Internal Authentication Flow

1. **On first run:**
   - Reads cookies from `.env.e2e`
   - Validates by accessing `/customer/list`
   - If cookies valid → uses them
   - If cookies expired → performs SSO login, saves fresh cookies, continues

2. **On subsequent runs:**
   - Reads fresh cookies from `.env.e2e`
   - Validates again
   - If cookies expired (2-hour JWT expiry) → auto-refreshes
   - User doesn't need to manually run tests

### Benefits

| Aspecto | Self-Contained Skill |
|--------|---------------------|
| **Setup** | pnpm dev (that's it!) |
| **Prerequisites** | None — handles auth internally |
| **Speed** | ~1-2s per page (reuses session) |
| **Auth** | Real SSO (same flow as E2E tests) |
| **Cookies** | Auto-refreshes when expired |
| **Testids** | Captured from rendered DOM |
| **Dependencies** | Playwright (already in project) |
| **Headless** | Always (no UI) |

## Configuration

File: `~/.claude/skills/testid-extractor/config.json`

```json
{
  "routes": [
    { "name": "Customer List", "path": "/customer/list" },
    { "name": "Customer Add Corporate", "path": "/customer/add/corporate" },
    { "name": "Customer Add Individual", "path": "/customer/add/individual" }
  ],
  "browser": "chromium",
  "timeout": 10000,
  "headless": true,
  "output": {
    "file": "docs/testid-map.md",
    "format": "markdown"
  }
}
```

## Output Format

`docs/testid-map.md`:

```markdown
# TestID Map — customers-manager-ui

Last updated: 2026-03-17 14:30:00

## Route: /customer/list

### Components & Testids

| Component | Type | TestID | Selector | Notes |
|-----------|------|--------|----------|-------|
| CustomerList | Root | a3b9f1c204 | [data-testid="a3b9f1c204"] | Main container |
| CustomerListTable | Table | a3b9f1c204 | [data-testid="a3b9f1c204"] | Rendered inside list |
| TableColumnHeader | Table Col | a3b9f1c204-col-0 | [data-testid="a3b9f1c204-col-0"] | Name column |
| TableColumnHeader | Table Col | a3b9f1c204-col-1 | [data-testid="a3b9f1c204-col-1"] | Email column |
| TableRow | Table Row | a3b9f1c204-row-0 | [data-testid="a3b9f1c204-row-0"] | First customer row |
| EditButton | Interactive | a3b9f1c204-row-0-button-0 | [data-testid="a3b9f1c204-row-0-button-0"] | Edit button in row |

### Tree Structure

```
a3b9f1c204 (CustomerList)
├── a3b9f1c204-col-0 (TableHeader)
├── a3b9f1c204-col-1 (TableHeader)
└── a3b9f1c204-row-0 (TableRow)
    ├── a3b9f1c204-row-0-button-0 (EditButton)
    └── a3b9f1c204-row-0-button-1 (DeleteButton)
```

---

## How Pattern Analyzer Uses This

Pattern analyzer references `docs/testid-map.md` to:

1. **Validate E2E selectors** — Ensures test uses existing `data-testid`
2. **Detect pattern violations** — Warns if test uses `data-test` instead of `data-testid`
3. **Suggest corrections** — Recommends correct selector from map

## Safety Rules

- Never modify generated hashes manually — they're computed by plugin
- Always regenerate after major component structure changes
- Update before each release cycle
- Keep `docs/testid-map.md` in version control as reference
- Skill handles auth internally — don't manually pass BASE_URL or env vars

## Tools

- `testid_extractor.py` — Main orchestrator using Node.js + Playwright
- `testid_parser.py` — Parse hashes and detect patterns
- `testid_map_generator.py` — Create markdown report
- `e2e/auth/` module — Reusable authentication logic (called internally)

## Dependencies

- playwright (already in project)
- @playwright/test (already in project)
- pathlib (built-in Python)
- re (built-in Python)
