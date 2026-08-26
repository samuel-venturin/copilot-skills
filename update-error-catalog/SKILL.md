---
name: update-error-catalog
description: Sync error codes from ErrorCatalog.cs (BFF) to frontend i18n localization files following the error-catalog.md conventions.
---

# Update Error Catalog Skill

## O que essa skill faz

Sincroniza os códigos de erro do backend (`ErrorCatalog.cs` no BFF) com os arquivos de localização do frontend (`i18n/locales/*.json`), seguindo as convenções definidas em `error-catalog.md`.

---

## Fluxo de execução

### 1. Localizar os arquivos de referência

**No frontend (projeto atual):**
```
i18n/locales/pt-BR.json
i18n/locales/en.json
error-catalog.md            ← convenções e estrutura esperada
```

**No BFF** — usar naming convention para encontrar o projeto:
- `<base>-ui` → `<base>-service` ou `<base>-manager-service`
- Buscar `ErrorCatalog.cs` em ordem de preferência:
  ```bash
  # Opção A: local
  find ~/projects/<bff-name> -name "ErrorCatalog.cs" 2>/dev/null
  git -C ~/projects/<bff-name> show origin/develop:<path/to/ErrorCatalog.cs>

  # Opção B: GitHub CLI
  gh api repos/scansource-brazil/<bff-name>/contents/ --jq '.[].path' | grep -i error
  gh api repos/scansource-brazil/<bff-name>/contents/<path>?ref=develop
  ```

### 2. Ler error-catalog.md

Antes de qualquer mudança, ler `error-catalog.md` completamente para entender:
- Estrutura de chaves esperada
- Convenção de nomes
- Quais arquivos de locale atualizar
- Regras de formatação das mensagens

### 3. Extrair códigos do ErrorCatalog.cs

Identificar todos os códigos de erro definidos no arquivo. Formato típico:
```csharp
public static class ErrorCatalog {
    public const string CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND";
    public const string INVALID_TAX_EXEMPTION = "INVALID_TAX_EXEMPTION";
    // ...
}
```

### 4. Comparar com os locales existentes

- Identificar códigos presentes no `ErrorCatalog.cs` mas **ausentes** nos JSONs → adicionar
- **Nunca remover** entradas existentes nos JSONs
- **Nunca alterar** traduções existentes (apenas adicionar)

### 5. Atualizar os arquivos de locale

Seguir exatamente a estrutura definida em `error-catalog.md`. Exemplo típico:
```json
{
  "errors": {
    "CUSTOMER_NOT_FOUND": "Cliente não encontrado.",
    "INVALID_TAX_EXEMPTION": "Isenção fiscal inválida."
  }
}
```

- `pt-BR.json` → mensagens em português
- `en.json` → mensagens em inglês
- Manter formatação e indentação existente do arquivo

### 6. Commitar as mudanças

Usar a skill `commit-changes` após as atualizações:
```bash
git commit -m "[TICKET][CHORE]: sync error catalog from BFF ErrorCatalog.cs"
```

---

## Regras obrigatórias

- ⛔ Nunca remover traduções existentes
- ⛔ Nunca alterar traduções existentes — apenas adicionar novas
- ⛔ Não fazer alterações fora do escopo (outros arquivos de i18n, lógica de componentes, etc.)
- ✅ Preservar formatação e estrutura dos arquivos JSON
- ✅ Sempre ler `error-catalog.md` antes de escrever qualquer coisa
- ✅ Sem testes unitários necessários para esta skill

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| `ErrorCatalog.cs` não encontrado localmente | Usar GitHub CLI com naming convention do BFF |
| Arquivos de locale não existem | Criar `i18n/locales/pt-BR.json` e `i18n/locales/en.json` seguindo estrutura do `error-catalog.md` |
| BFF com nome diferente do padrão | Perguntar ao usuário o nome exato do repositório |
