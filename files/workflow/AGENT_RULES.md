# AI AGENT OPERATING PROTOCOL

## PROJECT ARCHITECTURE

This repository follows a multi-tool AI workflow.

Tools used:

1. Claude Desktop
2. Gemini CLI
3. Aider
4. OpenCode

Each tool has STRICT responsibilities.

Agents/tools must NOT exceed their assigned scope.

---

# GLOBAL RULES

1. DO NOT rewrite unrelated systems.
2. DO NOT refactor architecture unless explicitly requested.
3. DO NOT modify files outside task scope.
4. ALWAYS preserve existing architecture patterns.
5. STOP when task exits assigned responsibility.
6. HAND OFF instead of overextending.
7. Prefer minimal safe changes over broad rewrites.
8. NEVER replace working systems unless instructed.
9. ALWAYS explain uncertainty before acting.
10. NEVER hallucinate missing architecture details.

---

# TOOL RESPONSIBILITIES

## 1. CLAUDE DESKTOP

ROLE:

* Architecture
* Planning
* Framework design
* System reasoning
* Workflow design
* Reviewing implementation strategy

ALLOWED:

* Design decisions
* Folder structures
* High-level patterns
* Technical specifications
* Development roadmaps

NOT ALLOWED:

* Large repo rewrites
* Autonomous debugging loops
* Runtime execution
* Massive implementation edits

STOP CONDITION:
If task becomes implementation-heavy or requires execution/testing.

HANDOFF TO:

* Aider for precise implementation
* OpenCode for execution/debugging
* Gemini CLI for large-context repo analysis

---

## 2. GEMINI CLI

ROLE:

* Large context understanding
* Repository analysis
* Long log inspection
* Dependency tracing
* Cross-file reasoning

ALLOWED:

* Reading large codebases
* Explaining architecture
* Finding bottlenecks
* Summarizing systems
* Identifying probable bugs

NOT ALLOWED:

* Large autonomous edits
* Broad architecture redesign
* Runtime execution loops

STOP CONDITION:
If changes need implementation or debugging execution.

HANDOFF TO:

* Aider for implementation
* OpenCode for runtime debugging

---

## 3. AIDER

ROLE:

* Precise implementation
* Small-to-medium scoped changes
* Surgical code modifications
* Repo-aware edits

ALLOWED:

* Targeted feature implementation
* Safe refactoring
* Small bug fixes
* Explicit file modifications

NOT ALLOWED:

* Full architecture redesign
* Runtime execution orchestration
* Massive repo rewrites
* Autonomous infrastructure debugging

STOP CONDITION:
If:

* task scope expands too broadly
* runtime execution is required
* debugging requires terminal feedback
* changes affect unrelated systems

HANDOFF TO:

* OpenCode for debugging/testing
* Claude for architectural clarification

---

## 4. OPENCODE

ROLE:

* Autonomous execution
* Runtime debugging
* Docker workflows
* Terminal execution
* Test fixing
* Build correction

ALLOWED:

* Running tests
* Fixing runtime errors
* Docker debugging
* Resolving imports
* Build stabilization
* Execution loops

NOT ALLOWED:

* Large architectural redesign
* Massive speculative rewrites
* Replacing stable systems unnecessarily

STOP CONDITION:
If:

* issue is architectural
* requirements are unclear
* debugging becomes speculative
* unrelated systems would be modified

HANDOFF TO:

* Claude for planning clarification
* Aider for precise implementation

---

# TASK ROUTING

Architecture issue?
→ Claude Desktop

Large repo understanding?
→ Gemini CLI

Precise implementation?
→ Aider

Execution/debugging/testing?
→ OpenCode

---

# IMPLEMENTATION PRINCIPLES

1. Prefer additive changes over destructive rewrites.
2. Keep functions modular.
3. Preserve existing interfaces when possible.
4. Avoid hidden side effects.
5. Respect current architecture patterns.
6. Explain risky modifications before applying them.

---

# CONTEXT MANAGEMENT

Agents should:

* load only relevant files
* avoid entire repo dumps
* summarize before expanding context
* avoid repeated context pollution

---

# FAILURE POLICY

If confidence is low:

1. STOP
2. Explain uncertainty
3. Request clarification
4. Suggest handoff

Do NOT fabricate solutions.

---

# PRIMARY GOAL

Maximize:

* code stability
* implementation precision
* debugging efficiency
* architectural consistency

Minimize:

* hallucination
* unnecessary rewrites
* token waste
* context collapse
* unrelated modifications
