# Context

The current CLI injects no host authority. `render build` invokes `require_release_support` before DOCX creation and classifies every exception as a renderer failure. The methodology explicitly permits work before final evidence and approval gates. Publication baseline is current origin/main; installed versioned files were compared byte-for-byte before editing.

# Decisions

1. Add an explicit `render draft` action. Keep `render build` and `release` strict and backward compatible. Store provisional artifacts under a draft namespace, with a distinct manifest type and fixed false authority flags. Never manufacture trusted receipts.
2. Reuse structural composition and rendering, without marking unverified claims verified. A visible working-draft notice and a separate review-gap list must survive DOCX and PDF conversion. Content is supplied by the agent from the dossier, not fabricated by the renderer.
3. Persist the exact input and output hashes. Status rechecks existing draft files; a modified or missing file cannot remain ready even as a working draft. A provisional manifest is never a release manifest.
4. Separate error categories and actionable messages. A missing host verifier must not recommend reinstalling the PDF converter.
5. Evaluation uses a frozen input manifest, explicit human/evaluator provenance and separate dimensions. A researchable case may remain legally unready. Successful research is not a GO decision; a refusal to claim filing-readiness is not automatically a false rejection.
6. Synthetic tests establish software behavior. Private complete-case rehearsal is local and produces a draft plus unresolved legal-review tasks. Human review and the actual court outcome remain external events, never simulated as completed.
7. No new LLM comparison is required for deterministic checks. Any later LLM experiment requires actual Langfuse traces and DeepEval records, without turning their scores into legal authority.

# Risks and Trade-offs

A provisional document may be mistaken for a final one. Use visible markings, separate storage/schema/status, gap report and false authority flags; test that release validation rejects it. Legal uncertainty remains explicit. Existing release protections and public/private boundaries stay intact.

# Verification

Test the installed-style CLI without host stubs, real DOCX/PDF conversion, artifact mutation, unsupported claims, provisional/final isolation, exact error categories and false-rejection distinctions. Run strict skill/runtime/source checks, clean-room install, OpenSpec and publication checks. Publish only generic methodology, code and synthetic fixtures; record private rehearsal evidence outside Git.
