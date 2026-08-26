---
id: IDEA-002
name: Task interpreter skill for specs
description: Interpret specs and suggest plan/parallel execution
applies_to: skill-orchestration
status: draft
priority: high
owner: team
created_at: 2026-02-27T18:10:00Z
last_updated: 2026-02-27T23:59:00Z
---

# IDEA-002 — Task interpreter skill for specs

## Revision Log (newest first)

### 2026-02-27T23:59:00Z — rev-13
#### User-approval safeguard before `done` + protected cleanup policy for `tasks/`

User requirement:
- Agent must not move a task to `done` before explicit user confirmation that the task is ready.
- Agent must not delete temporary task artifacts automatically at `done` transition.
- Cleanup should be optional and explicitly confirmed by user.
- Temporary artifact scope is all generated files inside `.github/skills/task-interpreter/tasks/`, but persistent files (such as templates) must be preserved.

Critical analysis:
- Benefit:
  - prevents premature closure and accidental loss of execution context;
  - keeps user in control of completion and artifact retention;
  - improves auditability and safety in multi-session execution.
- Risk:
  - completion can stall if confirmation contract is unclear;
  - broad cleanup rules can remove reusable helper artifacts if not protected.
- Mitigation:
  - introduce dedicated approval status before `done`;
  - require exact confirmation token (whitelist phrase), not semantic interpretation;
  - enforce cleanup whitelist and optional post-done prompt.

Rule update (v2.2):
1. Lifecycle update:
   - `new -> waiting -> doing -> awaiting-user-approval -> done`.
2. Completion approval gate:
   - `doing/awaiting-user-approval -> done` requires exact user token:
     - `APROVAR_DONE_IDEIA_002`.
   - semantic confirmations are not accepted for completion.
3. Post-done cleanup gate:
   - after transition to `done`, agent must ask whether to clean temporary artifacts;
   - default behavior without explicit confirmation: do not clean.
4. Cleanup scope and preservation:
   - cleanup candidate scope: generated artifacts in `.github/skills/task-interpreter/tasks/`;
   - mandatory preserve list:
     - `.gitkeep`
     - any file under `.github/skills/task-interpreter/tasks/templates/`
   - recommended removable patterns:
     - `*.prompt.md`
     - `*.quality.md`
     - `*.qa-second-pass.md`
5. Fail-safe policy:
   - in any ambiguity/timeout/parser uncertainty, keep status unchanged and skip cleanup.

Next step:
- update `task-interpreter` skill with `awaiting-user-approval` status, exact-token approval gate, and protected cleanup policy for `tasks/`.

### 2026-02-27T23:58:00Z — rev-12
#### Mandatory E2E validation in headed mode with playwright-cli + regression rerun

User requirement:
- Every flow validation must include at least one E2E execution with `playwright-cli` in `headed` mode.
- This is mandatory to visibly demonstrate to the user that the delivered flow works.
- Agent must not forget E2E: after finishing implementation, it must run current-screen E2E plus regression rerun of already validated tests to detect residual issues.

Critical analysis:
- Benefit:
  - raises confidence by validating real browser behavior with visible execution;
  - improves stakeholder trust through demonstrable functional evidence;
  - reduces unnoticed side effects by mandatory regression rerun.
- Risk:
  - increased validation time in large scopes;
  - flaky tests may block completion when not properly scoped.
- Mitigation:
  - define minimal required scope for current feature + impacted historical flows;
  - preserve evidence log with executed suites and outcomes;
  - if failures occur, keep task in `doing` and attach focused retest plan.

Rule update (v2.1):
1. Add `e2e_validation_gate` before allowing `doing -> done`.
2. `e2e_validation_gate` requirements:
   - execute E2E with `playwright-cli` in `headed` mode (mandatory);
   - include scenario for current screen/flow under implementation;
   - rerun relevant previously executed E2E tests as regression scope.
3. Evidence contract additions:
   - `e2e_runner`: `playwright-cli`
   - `e2e_mode`: `headed`
   - `e2e_current_flow_result`: pass|fail
   - `e2e_regression_result`: pass|fail
   - `e2e_evidence_path`: screenshots/log reference
4. Status transition policy impact:
   - block `doing -> done` if mandatory E2E (`headed`) was not executed;
   - block `doing -> done` if regression rerun is pending or failed.

Next step:
- update `task-interpreter` skill to enforce mandatory E2E headed via `playwright-cli` and regression rerun checklist.

### 2026-02-27T23:40:00Z — rev-11
#### Explicit trigger classes + decision matrix for task pickup vs execution

User requirement:
- Define explicit trigger classes so the agent can distinguish when to discover/plan tasks versus when to execute an already identified task prompt.
- Discovery/Planning should be activated by question-style daily-task prompts.
- Resume/Execute should be activated by direct order-style prompts, with or without explicit task name.
- Keep decision matrix as mandatory dispatch policy.

Trigger policy update (v2.0):
1. `trigger_class_discovery_planning` (question intent):
   - examples:
     - "o que temos pra hoje?"
     - "qual a boa do dia?"
     - "o que vamos fazer hoje?"
     - "quais tarefas temos pra hoje?"
     - "quais as tarefas do dia?"
   - required behavior:
     - always check tasks in `doing` first;
     - if `doing` exists, surface/prepare continuation context first;
     - then identify and plan new specs (`new`) if applicable.

2. `trigger_class_resume_execute` (direct order intent):
   - examples:
     - "continue com a adição de isenções fiscais."
     - "continua com a tarefa que estávamos fazendo ontem."
     - "segue o baile!"
   - required behavior:
     - pick already identified tasks in `doing`/`waiting`;
     - start or continue execution from existing prompt context.

3. Priority and fallback:
   - `doing` always has priority over `waiting/new` when execution intent is detected;
   - if multiple `doing` tasks exist, ask user to choose one;
   - if no `doing` exists, fallback to `waiting`, then `new` planning queue.

Decision matrix policy:
- Decision matrix is mandatory and must map:
  - detected trigger class,
  - task status availability (`doing|waiting|new`),
  - prompt artifact existence,
  - branch/context alignment,
  - resulting action.

Expected output additions:
- `trigger_class_detected`: `discovery-planning` | `resume-execute`
- `pickup_source_status`: `doing` | `waiting` | `new`
- `decision_matrix_path`: reference to active matrix/ruleset section

Next step:
- update task-interpreter operational skill with explicit trigger classes and mandatory decision matrix section.

### 2026-02-27T23:25:00Z — rev-10
#### Automatic resume policy for tasks in `doing` (no question flow)

User requirement:
- When a task already exists in `doing`, the agent must not ask whether to continue.
- Agent must run an automatic resume preflight with branch/worktree validation and scope adherence checks before continuing.

Critical analysis:
- Benefit:
  - removes unnecessary interaction friction in active tasks;
  - increases continuity and recovery quality after interrupted sessions;
  - reduces risk of accidental work in the wrong branch.
- Risk:
  - auto-branch switching can accidentally hide local work if not preserved first;
  - false-positive completion detection can incorrectly move index state.
- Mitigation:
  - enforce stash safeguard before checkout (`stash -u` with traceable message);
  - require explicit completion evidence before index status updates;
  - if changes diverge from prompt scope, force collaborative discussion mode (`!?`) before proceeding.

Rule update (v1.9):
1. If there is a task with status `doing`, enter `automatic_resume_mode` (no initial disambiguation question).
2. Compute expected branch from task contract and check whether current branch matches.
3. If current branch differs:
  - verify expected branch existence;
  - if branch exists, check completion evidence to detect `task completed but index stale`.
4. Completion evidence policy:
  - if completion is confirmed, update index status accordingly;
  - if not completed, inform branch switch action and continue resume flow.
5. Before switching branches, inspect current working tree:
  - if there are local changes to preserve, execute `git stash -u`;
  - stash message must identify agent + reason (automatic resume safety).
6. If current branch already matches task branch:
  - inspect local changes and compare with task prompt scope;
  - if changes are aligned, infer current stage and continue execution;
  - if changes are not aligned, stop execution and discuss next action with user in collaborative mode (`!?`).

Expected output additions:
- `resume_mode`: `automatic` | `manual`
- `resume_branch_check`: `matched` | `switched` | `missing-branch`
- `resume_stash_action`: `none` | `created`
- `resume_scope_alignment`: `aligned` | `misaligned`

Next step:
- extend `task-interpreter` operational flow and prompt/report contracts with `automatic_resume_mode` preflight states.

### 2026-02-27T22:05:00Z — rev-09
#### Quality artifact with CA/CT/DoD + dedicated QA verification agent

User requirement:
- Persist `CA/CT/DoD` into a dedicated quality file.
- After development, dispatch a dedicated quality agent for a second-pass verification against the spec-derived quality contract.

Critical analysis:
- Benefit:
  - objective traceability between implementation and acceptance/testing/done criteria;
  - enables independent QA pass without re-parsing whole spec each time;
  - improves handoff quality and reduces false “done” states.
- Risk:
  - quality file becoming stale if implementation evolves and artifact is not refreshed.
- Mitigation:
  - enforce refresh gate before QA dispatch;
  - include source hash/timestamp from spec and last sync timestamp in quality file metadata.

Rule update (v1.8):
1. Add `quality_contract_generation_gate` after spec parsing and before execution.
2. Generate/update quality artifact per task:
   - `.github/skills/task-interpreter/tasks/<task-slug>.quality.md`
3. Mandatory sections in quality artifact:
   - `acceptance_criteria` (normalized `CAxx` list),
   - `test_cases` (normalized `CTxx` list grouped by positive/negative/error),
   - `definition_of_done` (normalized checklist),
   - `traceability_matrix` (`CA/CT/DoD -> evidence/tests/files`),
   - `quality_gaps` (pending criteria/evidence).
4. Add `qa_second_pass_gate` after development completion:
   - dispatch dedicated QA agent with:
     - generated quality artifact,
     - task prompt,
     - changed files and test evidence.
5. QA agent output contract:
   - `qa_verdict`: `approved` | `approved-with-notes` | `rejected`,
   - `failed_items`: unmet `CA/CT/DoD` references,
   - `required_fixes`: actionable list,
   - `retest_scope`: focused validation plan.

Status transition policy impact:
- `doing -> done` requires QA second-pass result not `rejected`.
- If `rejected`, keep task in `doing` (or `waiting-fix` if this status is introduced later).

Expected output additions:
- `quality_artifact_path`
- `quality_sync_status` (in-sync | stale)
- `qa_second_pass_result`

Next step:
- extend task-interpreter scaffold to generate `<task-slug>.quality.md` and include QA second-pass dispatch in completion workflow.

### 2026-02-27T21:35:00Z — rev-08
#### Branch existence gate for resumed/completed task artifacts

User proposal:
- There may be completed task artifacts still present in `tasks/` and the agent may not know that work already exists.
- Before creating a new branch, interpreter should check whether the expected branch already exists.

Critical analysis:
- Benefit:
  - avoids duplicate branches and duplicated implementation attempts;
  - improves resume reliability for interrupted work.
- Risk:
  - false negatives when branch exists only on remote or branch naming drift occurred.
- Mitigation:
  - check both local and remote refs;
  - apply deterministic branch suggestion from ticket/type rules;
  - if branch mismatch is detected, ask focused reconciliation question.

Rule update (v1.7):
1. Add `branch_existence_gate` before branch creation.
2. For selected task/spec, compute `branch_name_suggestion`.
3. Validate existence in both scopes:
   - local branch refs;
   - remote branch refs (`origin`).
4. Behavior:
   - if branch exists: reuse branch and continue;
   - if branch does not exist: create branch;
   - if conflicting candidate branches exist: stop and ask user which one is canonical.

Prompt/index/report additions:
- `branch_exists_local`: boolean
- `branch_exists_remote`: boolean
- `branch_resolution`: `reuse-existing` | `create-new` | `user-decision-required`

Consistency note:
- Presence of `.prompt.md` file in `tasks/` must not imply branch creation is needed.
- Task selection should first reconcile: `index status` + `task artifact` + `branch existence`.

Next step:
- add branch existence check to task-interpreter execution preflight and include result in test-report metrics.

### 2026-02-27T21:10:00Z — rev-07
#### Commit checkpoints + prompt decomposition + strict orchestrator mode

User proposal:
- During task execution, progress should be persisted in Git history via commits at each completed stage, so future sessions can infer where execution stopped by reading branch commits.
- Instead of one long execution prompt, task output should contain multiple prompts, one per subtask, all preserving the same contract (`what`, `where`, `how`).
- The first agent should always act as an orchestrator-only role: dispatch subagents and delegate work, but never edit files directly.

Critical analysis:

1. **Commit-as-checkpoint policy**
   - Benefit:
     - durable progress tracking across interrupted sessions;
     - easier resume with objective audit trail per stage.
   - Risk:
     - commit spam/noise when stages are too granular;
     - low-quality checkpoints if no quality gate precedes commit.
   - Mitigation:
     - enforce checkpoint granularity by stage (not by file);
     - require minimum checkpoint criteria before commit:
       - related changes complete,
       - targeted tests executed (or explicitly skipped with reason),
       - short structured commit message.
   - Suggested commit message contract:
     - `[TICKET][TYPE]: stage <N>/<TOTAL> - <short action>`

2. **Prompt decomposition (one prompt per subtask)**
   - Benefit:
     - reduces cognitive overload;
     - improves parallelization and failure isolation.
   - Risk:
     - subtask drift if dependencies between prompts are implicit.
   - Mitigation:
     - add dependency metadata per prompt:
       - `stage_id`, `depends_on`, `inputs`, `outputs`, `done_criteria`.
     - keep a parent execution manifest referencing all stage prompts.

3. **Strict orchestrator-first model**
   - Benefit:
     - clearer separation between planning/orchestration and implementation;
     - better control over delegation and execution order.
   - Risk:
     - extra latency for very small tasks;
     - orchestration overhead if no parallel value exists.
   - Mitigation:
     - allow adaptive mode:
       - default `orchestrator-only` for medium/large tasks;
       - optional fast-path (single executor) for tiny low-risk tasks, only with explicit user opt-in.

Rule update (v1.6):
- Task output should be decomposed into stage prompts under:
  - `.github/skills/task-interpreter/tasks/<task-slug>/stage-<NN>-<name>.prompt.md`
- Add manifest file:
  - `.github/skills/task-interpreter/tasks/<task-slug>/manifest.prompt.md`
  - containing stage order, dependencies, and completion criteria.
- Introduce execution ledger:
  - `.github/skills/task-interpreter/tasks/<task-slug>/progress.md`
  - each completed stage records: timestamp, commit hash, status, evidence/tests.
- Orchestrator must not edit implementation files directly; it can only:
  - select next stage,
  - dispatch subagent(s),
  - validate completion gates,
  - register progress.

Open design note:
- Since commit operations may be restricted by execution policy or user preference, checkpoint behavior should support two modes:
  - `git-checkpoint` (preferred when allowed),
  - `no-git-checkpoint` (fallback using `progress.md` only).

Next step:
- extend `task-interpreter` scaffold to generate stage-based prompts + manifest + progress ledger and define checkpoint gates per stage.

### 2026-02-27T20:05:00Z — rev-06
#### Prompt-output contract + spec index lifecycle + branch naming

User decisions consolidated:
- The primary output of `task-interpreter` must be a high-precision prompt that tells agent(s) exactly **what**, **where**, and **how** to implement.
- Skill trigger can be dynamic/automated by scanning `specs/` and detecting new spec files absent from the skill index.
- Ticket source priority is XML `<key>` (official source).
- Branch prefix depends on XML `<type>` label with company naming pattern `[TIPO_TAREFA]/[TICKET]`.

Rule update (v1.5):

1. **Spec index registry (mandatory)**
   - File: `.github/skills/task-interpreter/index.md`
   - Table columns: `name | path | status`
   - Allowed status: `new | waiting | doing | done`
   - If a spec exists in `specs/` but not in index:
     - auto-register with `status = new`.

2. **Planner dispatch for new specs**
   - For a `new` spec, interpreter may dispatch a subagent in analyze/planning mode.
   - Result must be persisted as temporary task prompt in:
     - `.github/skills/task-interpreter/tasks/nome-da-tarefa.prompt.md`
   - Prompt file purpose:
     - reusable execution handoff for the active task (`doing`),
     - support continuous execution after completion when auto-continue is enabled.

3. **Temporary file lifecycle**
   - `*.prompt.md` in `tasks/` are temporary artifacts.
   - On status transition to `done`, corresponding prompt file must be deleted.

4. **Status ownership model**
   - Adopt hybrid model:
     - skill updates deterministic transitions (`new -> waiting`, `waiting -> doing`, `doing -> done`) when execution milestones are objective,
     - ask confirmation for ambiguous transitions.

5. **Auto-continuation policy**
   - Env flag: `TASK_INTERPRETER_AUTO_CONTINUE=true`.
   - When a task reaches `done` and flag is enabled:
     - select next candidate by Jira priority (`Highest` -> `Lowest`),
     - tie-breaker: older `created` first.

6. **Branch naming contract**
   - Ticket extraction priority:
     1) XML `<key>` (required primary);
     2) `<link>` suffix as fallback/validation.
   - Type mapping (exact labels accepted):
     - `História` -> `us/TICKET`
     - `Tarefa` or `Sub-tarefa` -> `us/task/TICKET`
     - `Bug`, `bug`, `Hotfix`, `Fix` -> `bug/TICKET`
   - If `<key>` and `<link>` ticket diverge:
     - raise blocking question before branch suggestion.

Expected output addition for interpreter report:
- `execution_prompt_path`: generated `.prompt.md` path
- `branch_name_suggestion`: computed from `<type>` + ticket
- `index_status_transition`: previous -> next
- `auto_continue_candidate`: next spec (when applicable)

Critical analysis:
- Benefit: creates a deterministic queue + handoff mechanism and reduces operator friction between tasks.
- Risk: stale index/task files when manual interventions happen outside the skill.
- Mitigation: add periodic consistency check (`specs` vs `index.md` vs `tasks/*.prompt.md`) before dispatch.

Next step:
- implement initial `task-interpreter` scaffold with:
  - index synchronizer,
  - prompt generator,
  - branch suggester,
  - cleanup hook on `done`.

### 2026-02-27T19:28:00Z — rev-05
#### Functional baseline detection + API/mock planning

User requirement:
- Before planning implementation, interpreter should detect whether the feature already has a baseline started in the current app.
- Example pattern: existing list page + add button + form page/modal + submit action route.

Rule update (v1.4):
- Add `feature_baseline_gate` before planning/execution.

`feature_baseline_gate` checks:
1. existing list screen for domain (e.g., tax exemptions list);
2. presence of expected UI entry-point (add/incluir button);
3. existing navigation route for create form;
4. existing repository/store submit path;
5. known API endpoint contract for create action.

Expected output additions:
- `baseline_detected`: true/false
- `baseline_matrix`:
  - `list_screen_present`
  - `add_button_present`
  - `create_route_present`
  - `submit_action_present`
  - `api_contract_present`
- `missing_contract_items`: list of missing technical decisions (route, method, payload, errors).

Behavior when contract is missing:
- Ask only focused questions to user (e.g., create route path, HTTP method, payload expectations).
- Do not block full planning; generate plan with explicit placeholders and assumptions.

Mock strategy requirement:
- If API/route is undefined or backend is unavailable, interpreter should include a mock plan:
  - identify where mock handlers should be added;
  - define minimal response contracts for success/error;
  - map which tests can run with mocks vs which require real API.

Critical analysis:
- Benefit: avoids starting implementation blind and reduces rework when feature is incremental.
- Risk: false negative on baseline detection due to naming mismatch.
- Mitigation: use multi-signal detection (route names, i18n labels, component/store/repo references) and confidence score.

Next step:
- include baseline detector outputs in `task-interpreter` analyze-only report and auto-append mock planning section when API contract is absent.

### 2026-02-27T19:20:00Z — rev-04
#### Automatic scope inference by workspace context

User decision:
- Scope should be auto-detected from the current workspace/project context.
- Ask the developer about scope only when ambiguity exists (e.g., multiple projects or low-confidence classification).

Rule update (v1.3):
- If workspace has exactly one project and confidence is high:
  - auto-assign project scope (e.g., frontend) without asking.
- Ask scope confirmation only when:
  1. multiple projects are detected in workspace, or
  2. project-type confidence is below threshold.

Suggested detector behavior:
- run a lightweight context detector tool that checks:
  - number of root projects/folders,
  - framework signatures (`nuxt.config`, `package.json`, `app/pages`, etc.),
  - language/runtime indicators.
- produce:
  - `workspace_projects_count`,
  - `project_type`,
  - `confidence_score`,
  - `needs_user_scope_confirmation`.

Critical impact:
- improves UX by removing unnecessary questions in single-project workspaces;
- reduces interpretation latency before planning.

Risk/mitigation:
- risk: false auto-classification in mixed repos;
- mitigation: confidence gate + explicit fallback question.

Next step:
- add this inference step to the future `task-interpreter` pre-analysis pipeline.

### 2026-02-27T19:12:00Z — rev-03
#### XML filtering rule (scope hardening)

User decision:
- The interpreter must ignore XML `comments` and `links` sections for task understanding.

Rationale:
- They are dynamic/non-deterministic metadata.
- They add noise and can bias interpretation away from stable task requirements.

Parser rule update (v1.2):
- **Include**: task summary, description content, acceptance criteria, test cases, DoR/DoD, core metadata.
- **Ignore**: comments, issue links, watcher/votes dynamics, and similar volatile sections.

Impact:
- lower parsing variance over time;
- cleaner requirement extraction;
- better reproducibility of analysis outputs.

Next step:
- implement explicit XML ignore-list in the future extractor tool.

### 2026-02-27T19:05:00Z — rev-02
#### Input format baseline confirmed

Spec input pattern for this project is now explicit:
- markdown file under `specs/`;
- Jira XML block embedded in the markdown body;
- Portuguese business text mixed with structured sections (CA, CT, DoR, DoD, comments, links).

Reference sample:
- `specs/adicionar-isenção-fiscal.md`

#### Parser contract updates (v1.1)

The future `task-interpreter` should parse, normalize, and expose at least:
1. **Meta**
  - Jira key (ex: `CTR-1072`), summary, status, priority, sprint.
2. **Scope split**
  - frontend requirements,
  - backend dependencies,
  - blocked conditions/dependencies from comments.
3. **Acceptance extraction**
  - CA list grouped and indexed (`CA01...`).
4. **Test extraction**
  - CT list grouped by positive/negative/error (`CT01...`).
5. **Execution readiness**
  - DoR checklist,
  - DoD checklist,
  - blockers inferred from comments and unresolved dependencies.

#### Critical analysis for this format

- **Main risk**: large XML body can dilute frontend-only scope and lead to over-implementation.
- **Mitigation**: require scope partition gate (frontend-only vs full-stack vs dependency-blocked).
- **Main side effect**: duplicated acceptance data (in description and customfields) may create inconsistent extraction.
- **Mitigation**: deterministic priority source order for fields.

#### Suggested deterministic extraction order
1. `description` rich text (primary narrative source)
2. `customfields` acceptance criteria (secondary validation source)
3. `comments` for blockers/dependency evidence

#### Next step
Build a lightweight extractor (tool) for `specs/*.md` + embedded Jira XML and validate output against `specs/adicionar-isenção-fiscal.md` in analyze-only mode.

### 2026-02-27T18:22:00Z — rev-01
#### v1 technical contract

**Inputs**
- `spec_path` (required): path to spec file, usually under `specs/*.md`.
- `execution_mode` (optional): `analyze-only` | `plan` | `plan-and-execute`.
- `parallel_allowed` (optional): boolean (default `false`).
- `constraints` (optional): stack, deadlines, non-functional requirements, forbidden areas.

**Outputs (minimum)**
- `scope_summary`: what must be delivered in plain language.
- `impacted_areas`: pages/components/composables/stores/contracts/tests likely affected.
- `file_targets`: candidate file list with confidence level.
- `test_strategy`: unit/integration/e2e coverage proposal.
- `open_questions`: blockers or ambiguities requiring user answer.
- `recommended_next_action`: one clear next step.

**Decision gates**
1. `spec_quality_gate`
  - If spec is incomplete/ambiguous, stop implementation and ask focused questions.
2. `parallel_safety_gate`
  - If overlapping file targets are detected between tracks, recommend sequential mode.
3. `confirmation_gate`
  - Before any code change, ask user to confirm: plan only vs execution.

#### Parallel policy (v1)

**When parallel is recommended**
- Workstreams have low file overlap, e.g.:
  - Track A: feature implementation;
  - Track B: unit tests for stable contracts;
  - Track C: docs/changelog updates.

**When parallel is NOT recommended**
- Same files/modules are likely to be touched by multiple tracks.
- Core contracts are still unstable.
- Spec has unresolved decisions.

**Fallback behavior**
- Auto-fallback to sequential execution when collision risk is high.
- Explain rationale before proceeding.

#### Risk model (quick)
- **Scope drift**: mitigated by explicit checklist tied to spec items.
- **Merge conflicts**: mitigated by overlap detection and sequential fallback.
- **False positives in impact mapping**: mitigated by confidence labels + user confirmation.

#### Success criteria for rev-01
- Given one spec file, skill returns full output contract without coding.
- Skill asks confirmation before planning/execution.
- Skill recommends parallel mode only when overlap risk is low.

#### Next step
Prototype `task-interpreter` skill skeleton and validate against one real file in `specs/` with `analyze-only` mode.

### 2026-02-27T18:10:00Z — new-idea
#### Context
Need a skill that reads a task from `specs/`, interprets what must be done based on current project files, and proposes execution strategy before coding.

#### Proposal
Create a `task-interpreter` skill that:
1. reads a provided spec file from `specs/*.md`;
2. maps requirements to impacted layers/files in the current codebase;
3. returns an implementation checklist (what to build, what to update, what to test);
4. asks user whether to:
   - generate a detailed plan;
   - execute with subagents in parallel (example: implementation + unit tests in parallel streams).

#### Expected behavior
- The skill should not jump directly to coding.
- It should first explain scope, dependencies, and unknowns.
- It should clearly propose optional execution modes (single-threaded vs parallel).

#### Critical analysis
- Potential value:
  - better predictability before changes;
  - stronger requirement coverage;
  - reduced rework.
- Risks / side effects:
  - parallel subagents may create merge conflicts in same files;
  - over-planning overhead for small specs;
  - false confidence if spec is ambiguous/incomplete.
- Security/usability concerns:
  - ensure no speculative implementation without user confirmation;
  - keep prompts concise to avoid cognitive overload.

#### Suggested guardrails
- Require explicit user confirmation before parallel execution.
- Detect overlapping file targets and auto-fallback to sequential mode when collision risk is high.
- Keep a minimum output contract:
  - scope summary,
  - impacted files,
  - test strategy,
  - open questions.

#### Open questions
- Should this be one standalone skill or part of an existing planning skill?
- Should parallel mode be opt-in per task only, or persist as user preference?
- Which threshold should trigger “parallel is not recommended”?

#### Next step
Draft v1 `task-interpreter` skill contract and test it against one existing spec in `specs/`.
