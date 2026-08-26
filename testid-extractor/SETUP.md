# TestID Extractor Setup Guide (Playwright Local)

## Prerequisites

✅ `pnpm dev` running
✅ `e2e/.env.e2e` configured
✅ Playwright installed (comes with project)

## Quick Start (5 minutes)

### 1. Verify Playwright is installed

```bash
# Check if Playwright is available
python3 ~/.claude/skills/testid-extractor/tools/testid_extractor.py --check-playwright
```

Expected:
```
✅ Playwright is installed
✅ Ready to extract testids!
```

If NOT installed:
```bash
# Option A: Via npm (if in this project)
npm install -D @playwright/test

# Option B: Via pip (system-wide)
pip install playwright
playwright install
```

### 2. Validate .env.e2e

```bash
python3 ~/.claude/skills/testid-extractor/tools/testid_extractor.py --validate-env
```

Expected:
```
✅ e2e/.env.e2e exists
✅ Found 2 credential lines
```

If NOT found:
```bash
cp e2e/.env.e2e.example e2e/.env.e2e
nano e2e/.env.e2e  # Add your credentials
```

### 3. Start dev server (Terminal 1)

```bash
pnpm dev
# Server at http://localhost:3000
```

### 4. Extract testids (Terminal 2)

```bash
python3 ~/.claude/skills/testid-extractor/tools/testid_extractor.py --extract-all
```

Expected output:
```
🔐 Authenticating via http://localhost:3000/login
✅ Authentication successful

📊 Extracting testids...
  📄 Customer List:           ✅ 145 testids
  📄 Customer Add Corporate:  ✅ 89 testids
  📄 Customer Edit:           ✅ 123 testids

============================================================
{
  "status": "success",
  "pages": {
    "Customer List": {
      "testids": ["a3b9f1c204", "a3b9f1c204-col-0", ...],
      "count": 145,
      "patterns": {"root": 1, "table-col": 12, "table-row": 45, ...}
    },
    ...
  },
  "total_testids": 357,
  "saved": ".testid-extraction.json"
}
============================================================
```

## Performance

Esperado por extração completa (5 páginas):
- **Login**: ~3-5s
- **Per page**: ~1-2s (reutiliza página)
- **Total**: ~10-15s

## How It Works

```
┌─ Playwright (headless)
│  ├─ 1. Inicia Chromium headless
│  ├─ 2. Cria contexto (sessão reutilizável)
│  └─ 3. Cria página dentro do contexto
│
├─ Autenticação (UMA VEZ)
│  ├─ 1. Navega para /login
│  ├─ 2. Preenche credenciais de .env.e2e
│  ├─ 3. Clica submit
│  └─ 4. Aguarda indicador de sucesso
│
├─ Loop por cada rota (reutiliza mesma página!)
│  ├─ 1. page.goto(/customer/list)
│  ├─ 2. Aguarda [data-testid] aparecer (Vue hydration)
│  ├─ 3. Extrai todos os testids do DOM
│  ├─ 4. Categoriza por padrão (root, table, list, etc)
│  └─ 5. Guarda resultado
│
└─ Salva .testid-extraction.json
```

## Configuration

Edit `~/.claude/skills/testid-extractor/tools/config.json`:

```json
{
  "routes": [
    {
      "name": "Customer List",
      "path": "/customer/list",
      "description": "Browse all customers"
    }
  ],
  "browser": {
    "type": "chromium",
    "headless": true,
    "slowmo": 0
  },
  "auth": {
    "env_file": "e2e/.env.e2e",
    "login_url": "/login",
    "email_selector": "[data-testid=\"input-email\"]",
    "password_selector": "[data-testid=\"input-password\"]",
    "submit_selector": "[data-testid=\"btn-login\"]",
    "success_indicator": "[data-testid=\"dashboard\"]",
    "timeout_after_login": 5000
  }
}
```

## Integration with Pattern Analyzer

Depois que tiver `.testid-extraction.json`:

```bash
# Analisar um arquivo E2E para padrões
/refactor --type pattern e2e/tests/customer/list.spec.ts
```

O pattern analyzer vai:
1. ✅ Carregar `.testid-extraction.json`
2. ✅ Extrair testids do arquivo e2e
3. ✅ Validar contra testids capturados
4. ✅ Flagrar inválidos ou hardcoded
5. ✅ Sugerir corrigir

## Troubleshooting

### ❌ "Cannot connect to http://localhost:3000"
```bash
# Solution: Certifique-se que pnpm dev está rodando
pnpm dev
```

### ❌ "Authentication failed"
```bash
# Solution: Verifique credenciais
cat e2e/.env.e2e | grep E2E_USER
# Teste login manualmente na aplicação
```

### ❌ "Playwright not installed"
```bash
# Solution:
pip install playwright
playwright install
```

### ❌ "Timeout waiting for [data-testid]"
```bash
# Solution: Aumente timeout em config.json
"timeout_after_login": 10000  # 10 segundos
```

### ❌ "Login selectors not found"
```bash
# Solution: Atualize config.json com seletores corretos
# Verifique inspect da página de login
[data-testid="input-email"]      ✅ Verifique se existe
[data-testid="input-password"]   ✅ Verifique se existe
[data-testid="btn-login"]        ✅ Verifique se existe
```

## Próximos Passos

1. ✅ Run `/testid-extractor --check-playwright`
2. ✅ Run `/testid-extractor --validate-env`
3. ✅ Run `pnpm dev`
4. ✅ Run `/testid-extractor --extract-all`
5. ✅ Use com `/refactor --type pattern`

---

**Arquivo gerado**: `.testid-extraction.json`
**Uso**: O `/refactor --type pattern` carrega e valida contra ele
