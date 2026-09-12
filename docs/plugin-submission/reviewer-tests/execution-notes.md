# Observed checks

The fixture validator passed: five positive cases, three negative cases, sixteen synthetic TXT fixtures, matching SHA-256 values and separate expected/actual fields. See [validation-report.json](validation-report.json).

The packaged TXT intake smoke passed against the **plugin 1.0.1 candidate**: integrity before/after and collector all returned exit code 0; four P01 files were read, their hashes matched, their texts were nonempty, and inputs remained unchanged. See [cli-smoke-report.json](cli-smoke-report.json). This report is tied to the version, base source commit, modified-tree flag and distribution-manifest hash recorded there. The candidate is not a published-source artifact; repeat the smoke on the final published package and record it in the external release receipt. It does not claim testing of a different submission version.

An initial runner attempt failed because it passed the platform's unresolved temporary-directory path to the runtime. The runner was corrected to resolve its own temporary directory before constructing the state path. The subsequent packaged check passed; the plugin itself was not changed for this check. The initial runner process exited with code 1 and produced no model result.

No model ran any of the eight review prompts. All `actual_model_result` entries remain `not_run` with null response, trace and reviewer verdict. The final submission binding in `review-tests.json` must be set to the actual submitted artifact; it is currently pending. No legal quality, production readiness, signing, payment or filing was assessed or performed.
