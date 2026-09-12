## Context
Источник — текущий canonical skillset и синхронизированный глобальный runtime. Включаются 15 ksrf-* и constitutional-comparative-research. Встраивание только Markdown потеряет 61+ Python-файл, схемы и проверку документов. Пакеты создаются сборкой; отдельную редактируемую копию методологии не ведём.

## Goals / Non-Goals
Goals: newcomers can start with natural language; full skill routing; reproducible portable payload; working local environment; web-compatible methodology/resources; clear actual tool availability; preserved provenance and human approval.
Non-goals: redistribute private corpora or credentials; replace CasusLegal/HUDOC services; create legal approval; silently deploy a multi-user cloud service or claim app-store acceptance.

## Decisions
1. Enrich existing ksrf-complaint-cycle with applicant entry and a focused reference. All specialist skills remain available. No user-authored JSON is required; agent prepares existing CLI payloads.
2. Build from canonical versioned file contract into fresh output outside Git. Include exact runtime files, license, scripts and distribution documentation; exclude source-only tests/evals, credentials, private data, symlinks. Compute per-file hashes and source revision. Web and desktop artifacts share source hashes.
3. Provide plugin-native metadata and reproducible distribution tooling. Browser package does not declare local MCP servers; ChatGPT uses available execution/file tools and honestly degrades when runtime is unavailable. Desktop executes the same bundled runtime. No implicit migration of accounts, memory, approvals or local data.
4. Environment adapter uses standard-library Python for diagnostics/CLI delegation and optionally creates an isolated external venv with declared pinned Python dependencies. Never pip-install into host interpreter. System dependencies are explicit (LibreOffice, Poppler, Tesseract rus/eng); reproducible container supplies them. Runtime state is outside installed package; plugin updates do not overwrite dossiers.
5. Diagnose actual pdftotext/pdftoppm, LibreOffice renderer path and OCR languages per operation. Missing renderer/OCR does not prevent document-grounded analysis or a labelled text draft. Preserve raw existing doctor result separately.
6. Optional MCP/hosted integration, if included, delegates narrow documented operations to the same runtime and never invents trusted approvals. Public HTTPS hosting, user authentication/storage retention and workspace import permissions require independent live verification before claiming browser execution of local tools.
7. Verification combines deterministic packaging/containment checks, clean installation, CLI subprocess smoke, synthetic document intake and working export, privacy scan and explicit manual/host-level capability gaps. Synthetic tests are software evidence, not legal quality proof.

## Risks / Trade-offs
ChatGPT account and execution capabilities vary. Package validity is not installation in every account. Connected services require each user's own access. OCR can be incomplete. OpenAI public catalog publication is external review. Preserve these as precise reported states.

## Migration Plan
Build and test source changes in clean worktree; publish one atomic canonical release; confirm live remote SHA; install global source only from published clean checkout. Publish reproducible plugin distribution with matching provenance and installation instructions. Keep original user checkouts intact.
