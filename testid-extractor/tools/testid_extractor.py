#!/usr/bin/env python3
"""
TestID Extractor - Extrai data-testid das páginas autenticadas
Internamente chama global-setup para autenticação sincronizada
"""

import sys
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime


def load_config(skill_dir: Path) -> dict:
    """Load routes from config.json"""
    # Try multiple locations
    possible_paths = [
        skill_dir / "config.json",  # In tools/ directory
        skill_dir.parent / "config.json",  # In parent (skills/testid-extractor/)
    ]

    for config_file in possible_paths:
        if config_file.exists():
            with open(config_file, "r") as f:
                return json.load(f)

    return {"routes": []}


def create_extraction_test(project_root: Path, config: dict) -> Path:
    """Create a test file that Playwright can run to extract testids"""

    # Build routes list from config
    routes_json = json.dumps(config.get("routes", []))

    test_content = f"""import {{ test, expect }} from '@playwright/test';
import {{ getAuthenticatedContext, closeAuthContext }} from '../../auth/index';

test.describe('TestID Extraction', () => {{
  test('extract testids from all routes', async () => {{
    const baseUrl = process.env.BASE_URL || 'http://localhost:3001';

    const authContext = await getAuthenticatedContext({{
      baseUrl,
      headless: true,
    }});

    try {{
      console.log('\\n🔍 === TESTID EXTRACTOR ===\\n');

      const results = {{
        status: 'success',
        timestamp: new Date().toISOString(),
        base_url: baseUrl,
        pages: {{}},
        total_testids: 0,
        errors: []
      }};

      const configRoutes = {routes_json};

      console.log(`\\n📊 === EXTRAINDO TESTIDS (${{configRoutes.length}} rotas) ===\\n`);

      for (const route of configRoutes) {{
        process.stdout.write(`  📄 ${{route.name}}: `);

        try {{
          const url = baseUrl + route.path;
          await authContext.page.goto(url, {{ waitUntil: 'domcontentloaded', timeout: 10000 }});
          await authContext.page.waitForSelector('[data-testid]', {{ timeout: 5000 }});
          await new Promise(r => setTimeout(r, 500));

          const testids = await authContext.page.locator('[data-testid]').all()
            .then(els => Promise.all(els.map(el => el.getAttribute('data-testid'))))
            .then(ids => [...new Set(ids.filter(Boolean))].sort());

          results.pages[route.name] = {{
            status: 'captured',
            path: route.path,
            testids: testids,
            count: testids.length,
            captured_at: new Date().toISOString()
          }};

          results.total_testids += testids.length;
          console.log(`✅ ${{testids.length}} testids`);

        }} catch (err) {{
          console.log(`❌ ${{err.message}}`);
          results.errors.push({{
            path: route.path,
            error: err.message
          }});
        }}
      }}

      console.log('\\n✅ Extração concluída!\\n');
      console.log(JSON.stringify(results, null, 2));

      // Validate extraction was successful
      expect(results.total_testids).toBeGreaterThan(0);

    }} finally {{
      await closeAuthContext(authContext);
    }}
  }});
}});
"""

    # Create a temporary test file in the e2e/tests directory
    test_dir = project_root / "e2e" / "tests" / ".extraction"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_path = test_dir / "extract.spec.ts"

    with open(test_path, "w") as f:
        f.write(test_content)

    return test_path


def parse_extraction_results(output: str) -> dict:
    """Parse JSON results from test output"""
    # Extract JSON from output (looks for {...} pattern)
    json_match = re.search(r'\{[\s\S]*"total_testids"[\s\S]*\}', output)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return None
    return None


def generate_testid_map(results: dict) -> str:
    """Generate markdown documentation from extraction results"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    markdown = f"""# TestID Map — customers-manager-ui

**Last updated:** {timestamp}
**Total testids:** {results['total_testids']}
**Extraction timestamp:** {results['timestamp']}

---

"""

    for page_name, page_data in results['pages'].items():
        if page_data['status'] != 'captured':
            continue

        markdown += f"""## Route: `{page_data['path']}`

**Status:** {page_data['status']}
**TestID Count:** {page_data['count']}
**Captured at:** {page_data['captured_at']}

### TestIDs

```
{', '.join(page_data['testids'])}
```

### Summary

| Property | Value |
|----------|-------|
| Route | `{page_data['path']}` |
| Total TestIDs | {page_data['count']} |
| Captured | {page_data['captured_at']} |

---

"""

    return markdown


def save_artifacts(project_root: Path, results: dict) -> None:
    """Save extraction results to artifacts"""
    docs_dir = project_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON extraction
    json_file = docs_dir / ".testid-extraction.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"   📁 {json_file}")

    # Save markdown map
    markdown = generate_testid_map(results)
    md_file = docs_dir / "testid-map.md"
    with open(md_file, "w") as f:
        f.write(markdown)
    print(f"   📁 {md_file}")


def main():
    project_root = Path.cwd()
    while project_root != project_root.parent:
        if (project_root / ".git").exists():
            break
        project_root = project_root.parent

    env_file = project_root / "e2e" / ".env.e2e"
    if not env_file.exists():
        print("❌ e2e/.env.e2e não encontrado")
        return 1

    # Load config from skill directory
    skill_dir = Path(__file__).parent.parent
    config = load_config(skill_dir)

    if not config.get("routes"):
        print("❌ Nenhuma rota configurada em config.json")
        return 1

    print("✅ Configuração OK")
    print(f"   📋 {len(config['routes'])} rotas configuradas:\n")
    for route in config["routes"]:
        print(f"      • {route['name']} → {route['path']}")
    print()

    test_path = create_extraction_test(project_root, config)

    try:
        # Run the extraction test using Playwright and capture output
        result = subprocess.run(
            ["pnpm", "playwright", "test", str(test_path), "--headed"],
            cwd=str(project_root),
            capture_output=True,
            text=True
        )

        # Parse results from output
        output = result.stdout + result.stderr
        results = parse_extraction_results(output)

        if results and results.get('total_testids', 0) > 0:
            print("\n📊 === SALVANDO ARTEFATOS ===\n")
            save_artifacts(project_root, results)
            print(f"\n✅ Extraction concluída com sucesso: {results['total_testids']} testids extraídos\n")
        else:
            print("\n❌ Falha ao extrair testids\n")
            print(output)
            return 1

        # Cleanup
        try:
            import shutil
            shutil.rmtree(test_path.parent, ignore_errors=True)
        except:
            pass

        return result.returncode
    except FileNotFoundError:
        print("❌ Playwright não encontrado")
        return 1
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
