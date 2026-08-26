---
name: refactor
description: Single-entry refactoring automation with Python tools for code analysis, spec generation, and guided refactoring with user approval.
---

# Refactor Skill

Use this as the single skill for refactoring when the user asks to:
- automate code analysis and refactoring suggestions;
- generate refactoring specs with detailed guidance;
- apply refactoring changes with user approval;
- analyze tasks or features for improvement opportunities.

## Invocation

```bash
/refactor <path> --type <type>                    # Analyze single file
/refactor --type <type> --feature <feature>      # Analyze entire feature
/refactor --type <type> --task <CTR-####>        # Analyze task files
```

## Supported Refactoring Types

- **RDC** - Remove Dead Code (unused functions, variables, imports)
- **SE** - Simplify Expressions (reduce complexity, improve readability)
- **naming** - Naming Conventions (standardize variable/function names)
- **clean** - Clean Code (SOLID principles, DRY, best practices)
- **pattern** - Project Pattern Conformance (AGENTS.md, e2e/docs patterns)

## Runtime Model

All logic runs through Python scripts in:
- `~/.claude/skills/refactor/tools`

Central configuration lives in:
- `~/.claude/skills/refactor/tools/config.json`

`refactor_dispatcher.py` is the main entrypoint.

## Execution Model (Two-Phase)

### Phase 1 (Analysis / Spec Generation)

```bash
python3 ~/.claude/skills/refactor/tools/refactor_dispatcher.py \
  --type <type> \
  --path <path> \
  [--feature <feature>] \
  [--task <CTR-####>]
```

Expected output:
- `.refac.spec` files generated in `docs/refac/<feature|task>/`
- Detailed guidance: what to change, where, and why
- User review before execution

### Phase 2 (Confirmed Execution)

```bash
python3 ~/.claude/skills/refactor/tools/refactor_dispatcher.py \
  --type <type> \
  --path <path> \
  --apply
```

Applies refactoring changes based on spec guidance.

## Spec Format

All specs follow this structure:

```markdown
---
feature: <feature_name>
arquivo: <file_path>
tipo: <type> (<description>)
arquivos_relacionados: <related_files>
porque: <reason_for_refactoring>
---

# <file>-refac.spec

## Melhorias identificadas
[List of issues found]

## Por que mudar
[Rationale for changes]

## Como
[Detailed step-by-step instructions]

## Onde
[Specific line numbers or code sections]

## O que
[Exact code to be changed - TO-BE state]
```

## File Structure

```
~/.claude/skills/refactor/
├── SKILL.md                              ← This file
├── sub-skills/
│   ├── rdc/SKILL.md                      ← Remove Dead Code sub-skill
│   ├── se/SKILL.md                       ← Simplify Expressions sub-skill
│   ├── naming/SKILL.md                   ← Naming Conventions sub-skill
│   └── clean/SKILL.md                    ← Clean Code sub-skill
└── tools/
    ├── refactor_dispatcher.py            ← Main orchestrator
    ├── rdc_analyzer.py                   ← Dead code detection
    ├── se_analyzer.py                    ← Expression simplification
    ├── naming_analyzer.py                ← Naming conventions
    ├── clean_analyzer.py                 ← Clean code violations
    ├── spec_generator.py                 ← Spec file generation
    ├── file_ops.py                       ← File operations (create, read, write)
    └── config.json                       ← Configuration
```

## Safety Rules

- Never apply refactoring without explicit `--apply` flag.
- Always generate specs before showing diffs.
- Always ask for user confirmation before applying changes.
- Never overwrite original files without backup.
- Keep output machine-readable (JSON) for deterministic chaining.

## Environment Setup

The skill automatically:
- Creates `.venv` if not present
- Installs required Python dependencies
- Configures paths for analysis

## Output

All operations return JSON with:
- `status`: `success`, `needs_confirmation`, `blocked`, `error`
- `specs`: array of generated spec files
- `diff_summary`: before/after preview (if applicable)
- `next_action`: required user action
