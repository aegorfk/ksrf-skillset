#!/usr/bin/env python3
"""Experiment-only, hashes-only local telemetry and deterministic DeepEval checks.

No production prompts, LLM providers, or semantic-grounding claims are created.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import uuid


EXPERIMENT = "ksrf-ten-method-development-v1"
LANGFUSE_URL = "http://localhost:3001"
DIMENSIONS = (
    "source_fidelity", "inferential_validity", "strongest_objection",
    "lawful_effective_relief", "calibrated_uncertainty",
)
CALLS = ("baseline", "candidate", "review-forward", "review-reversed")
HYPOTHESES = tuple(f"H{i}" for i in range(1, 11))
REPO_ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_json(path: Path, value: object) -> None:
    """Publish an atomic 0600 report only outside the versioned checkout."""
    path = path.resolve()
    if path == REPO_ROOT or REPO_ROOT in path.parents:
        raise ValueError("Experiment reports must stay outside the checkout")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".probe-report-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def locator_diagnostic(citations: list, sources: list) -> dict:
    """Exact locator spelling is verified; narrower spellings remain unknown."""
    known = {item["source_id"]: item["locator"] for item in sources}
    if len(known) != len(sources):
        raise ValueError("Duplicate source identifiers")
    counts = {"exact": 0, "unverified_locator": 0, "invalid": 0}
    for citation in citations:
        sid, locator = citation.get("source_id"), citation.get("locator")
        if sid not in known or not isinstance(locator, str) or not locator.strip():
            counts["invalid"] += 1
        elif locator == known[sid]:
            counts["exact"] += 1
        else:
            counts["unverified_locator"] += 1
    score = (0.0 if counts["invalid"] else None if not citations or
             counts["unverified_locator"] else 1.0)
    return {**counts, "citation_count": len(citations), "score": score,
            "status": "unknown" if score is None else "invalid" if score == 0 else "exact",
            "semantic_grounding_verified": False}


def deepeval_types():
    # These are process-local settings, with no model or Confident cloud upload.
    os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
    os.environ["DEEPEVAL_UPDATE_WARNING_OPT_OUT"] = "YES"
    os.environ.pop("CONFIDENT_API_KEY", None)
    from deepeval.metrics import BaseMetric
    from deepeval.test_case import LLMTestCase

    class SourceLocatorMetric(BaseMetric):
        threshold = 1.0
        async_mode = False
        verbose_mode = False

        def measure(self, test_case, *args, **kwargs):
            payload = test_case.metadata
            self.diagnostic = locator_diagnostic(payload["citations"], payload["sources"])
            self.score = self.diagnostic["score"]
            self.skipped = self.score is None
            self.success = None if self.skipped else self.score == 1.0
            return self.score

        async def a_measure(self, test_case, *args, **kwargs):
            return self.measure(test_case)

        def is_successful(self):
            return self.success

        @property
        def __name__(self):
            return "Source locator integrity (mechanical only)"

    class FrozenJudgeDimensionMetric(BaseMetric):
        threshold = None
        async_mode = False
        verbose_mode = False

        def __init__(self, dimension: str):
            if dimension not in DIMENSIONS:
                raise ValueError("Unknown frozen judge dimension")
            self.dimension = dimension

        def measure(self, test_case, *args, **kwargs):
            item = test_case.metadata["dimension"]
            value = item["score"]
            if item["name"] != self.dimension or (value is not None and
                    (type(value) is not int or value not in (0, 1, 2))):
                raise ValueError("Invalid frozen judge score")
            self.score = None if value is None else float(value)
            self.skipped = value is None
            # This is a consumed model judgment, not an automatic acceptance gate.
            self.success = None
            self.reason = item["reason"]
            return self.score

        async def a_measure(self, test_case, *args, **kwargs):
            return self.measure(test_case)

        def is_successful(self):
            return None

        @property
        def __name__(self):
            return "Frozen model judgment: " + self.dimension

    return LLMTestCase, SourceLocatorMetric, FrozenJudgeDimensionMetric


def _metric_case(test_case_type, metadata: dict, output: object):
    return test_case_type(input=EXPERIMENT, actual_output=json.dumps(output, ensure_ascii=False),
                          metadata=metadata)


def load_runner(snapshot: Path, expected_hash: str):
    if file_hash(snapshot) != expected_hash:
        raise ValueError("Executed runner snapshot hash mismatch")
    spec = importlib.util.spec_from_file_location("frozen_argument_probe_runner", snapshot)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_receipt(run_dir: Path, hypothesis: str, call: str,
                     runner_snapshot: Path | None = None) -> tuple[dict, object | None]:
    directory = run_dir / hypothesis
    metadata = read_json(directory / f"{call}.metadata.json")
    if (metadata.get("experiment_id") != EXPERIMENT or
            metadata.get("hypothesis_id") != hypothesis or metadata.get("call_id") != call or
            metadata.get("status") not in {"completed", "failed", "running"}):
        raise ValueError("Run receipt binding mismatch")
    review = call.startswith("review")
    expected_kind = "review" if review else "trial"
    if (metadata.get("kind") != expected_kind or
            metadata.get("prompt_version") != EXPERIMENT + "." + expected_kind or
            metadata.get("model") != "gpt-6-astra" or
            metadata.get("provider") != "openai_via_codex_cli" or
            metadata.get("model_reasoning_effort") != "xhigh" or
            metadata.get("service_tier") != "priority"):
        raise ValueError("Run prompt/model configuration mismatch")
    runner_snapshot = runner_snapshot or REPO_ROOT / "tools/run_argument_method_probe.py"
    runner = load_runner(runner_snapshot, metadata.get("tool_sha256"))
    frozen_packet = read_json(directory / "packet.json")
    runner.validate_packet(frozen_packet)
    if frozen_packet["hypothesis_id"] != hypothesis or canonical_hash(frozen_packet) != metadata.get("packet_sha256"):
        raise ValueError("Frozen run packet binding mismatch")
    if review:
        _, baseline = validate_receipt(run_dir, hypothesis, "baseline", runner_snapshot)
        _, candidate = validate_receipt(run_dir, hypothesis, "candidate", runner_snapshot)
        if baseline is None or candidate is None:
            raise ValueError("Review inputs are not completed arms")
        expected_prompt = runner.build_review_prompt(frozen_packet, baseline, candidate,
                                                    reverse=call == "review-reversed")
    else:
        expected_prompt = runner.build_trial_prompt(frozen_packet, call)
    prompt = directory / f"{call}.prompt.txt"
    if (file_hash(prompt) != metadata.get("prompt_sha256") or
            hashlib.sha256(expected_prompt.encode()).hexdigest() != metadata.get("prompt_sha256")):
        raise ValueError("Prompt hash mismatch")
    output = None
    if metadata["status"] == "completed":
        output_path = directory / f"{call}.json"
        if file_hash(output_path) != metadata.get("output_sha256"):
            raise ValueError("Output hash mismatch")
        output = read_json(output_path)
        runner.validate_output(output, review=review)
    return metadata, output


def diagnose(packets_dir: Path, run_dir: Path, hypotheses: tuple[str, ...],
             runner_snapshot: Path | None = None) -> dict:
    test_case_type, locator_type, dimension_type = deepeval_types()
    rows, missing = [], []
    for hypothesis in hypotheses:
        packet_path = packets_dir / f"{hypothesis}.json"
        if not packet_path.is_file():
            missing.append({"hypothesis_id": hypothesis, "kind": "packet"})
            continue
        packet = read_json(packet_path)
        sources = packet["sources"]
        for source in sources:
            if hashlib.sha256(source["text"].encode()).hexdigest() != source["text_sha256"]:
                raise ValueError("Packet source text hash mismatch")
        for call in CALLS:
            if not (run_dir / hypothesis / f"{call}.metadata.json").is_file():
                missing.append({"hypothesis_id": hypothesis, "call_id": call})
                continue
            metadata, output = validate_receipt(run_dir, hypothesis, call, runner_snapshot)
            if metadata.get("packet_sha256") != canonical_hash(packet):
                raise ValueError("Run packet hash mismatch")
            row = {"hypothesis_id": hypothesis, "call_id": call,
                   "status": metadata["status"], "packet_sha256": canonical_hash(packet),
                   "metadata_sha256": file_hash(run_dir / hypothesis / f"{call}.metadata.json"),
                   "output_sha256": metadata.get("output_sha256"), "metrics": []}
            rows.append(row)
            if output is None:
                continue
            if call in {"baseline", "candidate"}:
                metric = locator_type()
                metric.measure(_metric_case(test_case_type,
                               {"citations": output["citations"], "sources": sources}, output))
                row["locator_diagnostic"] = metric.diagnostic
                continue
            labels = [assessment["label"] for assessment in output["assessments"]]
            if sorted(labels) != ["A", "B"]:
                raise ValueError("Review must contain exactly A and B")
            for assessment in output["assessments"]:
                names = [item["name"] for item in assessment["dimensions"]]
                if sorted(names) != sorted(DIMENSIONS):
                    raise ValueError("Frozen review dimensions are missing or duplicated")
                for item in assessment["dimensions"]:
                    metric = dimension_type(item["name"])
                    metric.measure(_metric_case(test_case_type, {"dimension": item}, output))
                    citation_metric = locator_type()
                    citation_metric.measure(_metric_case(test_case_type,
                        {"citations": item["citations"], "sources": sources}, output))
                    row["metrics"].append({"label": assessment["label"],
                        "dimension": item["name"], "score": metric.score,
                        "status": "unknown" if metric.score is None else "consumed_frozen_judgment",
                        "reason_sha256": hashlib.sha256(item["reason"].encode()).hexdigest(),
                        "locator_diagnostic": citation_metric.diagnostic,
                        "coverage": assessment["coverage"],
                        "critical_defect_count": len(assessment["critical_defects"]),
                        "human_review": False})
    completed = sum(row["status"] == "completed" for row in rows)
    return {"experiment_id": EXPERIMENT, "deepeval_version": importlib.metadata.version("deepeval"),
            "scope": list(hypotheses), "rows": rows, "missing": missing,
            "expected_calls_in_scope": 4 * len(hypotheses), "completed_calls": completed,
            "scope_complete": not missing and completed == 4 * len(hypotheses),
            "all_ten_complete": len(hypotheses) == 10 and not missing and completed == 40,
            "semantic_grounding_automated": False, "legal_quality_established": False,
            "unknown_score_count": sum(m["score"] is None for row in rows for m in row["metrics"])}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256((json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")) + "\n").encode()).hexdigest()


def langfuse_client(env_file: Path):
    """Read exactly the local project credentials in process, never emit them."""
    from dotenv import dotenv_values
    from langfuse import Langfuse
    values = dotenv_values(env_file)
    public = values.get("LANGFUSE_INIT_PROJECT_PUBLIC_KEY")
    secret = values.get("LANGFUSE_INIT_PROJECT_SECRET_KEY")
    if not public or not secret:
        raise RuntimeError("Local Langfuse project credentials are unavailable")
    client = Langfuse(public_key=public, secret_key=secret, base_url=LANGFUSE_URL,
                      environment=EXPERIMENT, timeout=10, flush_at=1)
    if not client.auth_check():
        raise RuntimeError("Local Langfuse authentication failed")
    return client


def readback(client, trace_id: str, *, expected_hash: str,
             score_names: set[str], timeout: float = 40,
             expected_scores: dict | None = None,
             expected_generations: dict | None = None) -> dict:
    """Require authenticated trace, observation and score visibility after flush."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            trace = client.api.trace.get(trace_id=trace_id)
            meta = trace.metadata or {}
            observations = trace.observations or []
            scores = trace.scores or []
            present = {score.name for score in scores}
            observed_scores = {score.name: score.value for score in scores}
            generations = {obs.name: obs for obs in observations if obs.type == "GENERATION"}
            generation_match = all(
                name in generations and generations[name].metadata.get("receipt_sha256") == receipt_hash
                for name, receipt_hash in (expected_generations or {}).items())
            scores_match = all(observed_scores.get(name) == value
                               for name, value in (expected_scores or {}).items())
            if (trace.id == trace_id and trace.name == EXPERIMENT
                    and meta.get("experiment_id") == EXPERIMENT
                    and meta.get("artifact_sha256") == expected_hash
                    and observations and score_names <= present and scores_match and generation_match):
                return {
                    "experiment_id": EXPERIMENT, "trace_id": trace_id,
                    "trace_url": client.get_trace_url(trace_id=trace_id),
                    "authenticated_readback": True,
                    "artifact_sha256": expected_hash,
                    "observation_count": len(observations),
                    "generation_count": len(generations),
                    "score_count": len(scores), "score_names": sorted(present),
                    "langfuse_version": importlib.metadata.version("langfuse"),
                    "content_policy": "hashes-and-non-reconstructive-metadata-only",
                }
        except Exception:
            # Backend indexing is asynchronous. Never expose a response body or keys.
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError("Langfuse trace/score readback incomplete")
        time.sleep(1)


def preflight(env_file: Path) -> dict:
    from langfuse import propagate_attributes
    client = langfuse_client(env_file)
    trace_id = uuid.uuid4().hex
    artifact_hash = digest({"experiment_id": EXPERIMENT, "purpose": "preflight",
                            "nonce": uuid.uuid4().hex})
    metadata = {"experiment_id": EXPERIMENT, "purpose": "preflight",
                "artifact_sha256": artifact_hash, "source_text_logged": False}
    try:
        with client.start_as_current_observation(
            name="experiment-preflight", as_type="span",
            trace_context={"trace_id": trace_id}, metadata=metadata,
        ):
            with propagate_attributes(trace_name=EXPERIMENT, tags=[EXPERIMENT],
                                      metadata={"experiment_id": EXPERIMENT,
                                                "artifact_sha256": artifact_hash}):
                pass
        client.create_score(trace_id=trace_id, name="preflight_receipt", value=1,
                            data_type="NUMERIC", metadata={"experiment_id": EXPERIMENT})
        client.flush()
        return readback(client, trace_id, expected_hash=artifact_hash,
                        score_names={"preflight_receipt"})
    finally:
        client.shutdown()


def telemetry_metadata(metadata: dict) -> dict:
    """Allowlist and validate values; arbitrary runner text can never reach telemetry."""
    fixed = {"experiment_id": EXPERIMENT, "model": "gpt-6-astra",
             "provider": "openai_via_codex_cli", "model_reasoning_effort": "xhigh",
             "service_tier": "priority"}
    for key, expected in fixed.items():
        if metadata.get(key) != expected:
            raise ValueError("Unregistered experiment model configuration")
    if metadata.get("hypothesis_id") not in HYPOTHESES or metadata.get("call_id") not in CALLS:
        raise ValueError("Unregistered hypothesis or call")
    result = {**fixed, "hypothesis_id": metadata["hypothesis_id"], "call_id": metadata["call_id"]}
    if metadata.get("status") not in {"completed", "failed"}:
        raise ValueError("Only completed or retained failed calls may be instrumented")
    result["status"] = metadata["status"]
    for key in ("prompt_sha256", "output_sha256", "tool_sha256", "packet_sha256"):
        value = metadata.get(key)
        if key == "output_sha256" and value is None and metadata["status"] == "failed":
            result[key] = None
        elif not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("Invalid telemetry artifact digest")
        else:
            result[key] = value
    result["prompt_version"] = EXPERIMENT + (".review" if metadata["call_id"].startswith("review") else ".trial")
    for key in ("elapsed_seconds", "price"):
        value = metadata.get(key)
        if value is not None and (type(value) not in (int, float) or
                                  not math.isfinite(value) or value < 0):
            raise ValueError("Invalid timing or price metadata")
        result[key] = value
    result["price_unknown"] = metadata.get("price") is None
    result["isolation_sha256"] = digest(metadata.get("isolation"))
    result["error_sha256"] = digest({"class": metadata.get("error_class"),
                                    "detail_type": metadata.get("error_detail_type")})
    usage = metadata.get("token_usage")
    result["token_usage"] = None
    if isinstance(usage, dict):
        result["token_usage"] = {}
        for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
            value = usage.get(key)
            if value is not None:
                if type(value) is not int or value < 0:
                    raise ValueError("Invalid token usage")
                result["token_usage"][key] = value
    result["source_text_logged"] = False
    return result


def publish(run_dir: Path, diagnostics_path: Path, env_file: Path,
            hypotheses: tuple[str, ...], runner_snapshot: Path | None = None) -> dict:
    from langfuse import propagate_attributes
    diagnostics = read_json(diagnostics_path)
    if diagnostics.get("experiment_id") != EXPERIMENT:
        raise ValueError("Diagnostics experiment mismatch")
    prepared, scores, missing = [], {}, []
    selected_unknown = 0
    indexed = {(row["hypothesis_id"], row["call_id"]): row for row in diagnostics["rows"]}
    for hypothesis in hypotheses:
        for call in CALLS:
            path = run_dir / hypothesis / f"{call}.metadata.json"
            if not path.is_file():
                missing.append(f"{hypothesis}.{call}")
                continue
            metadata, output = validate_receipt(run_dir, hypothesis, call, runner_snapshot)
            if metadata["status"] == "running":
                missing.append(f"{hypothesis}.{call}")
                continue
            row = indexed.get((hypothesis, call))
            if not row or row["metadata_sha256"] != file_hash(path):
                raise ValueError("Diagnostics do not bind the current run receipt")
            if row["packet_sha256"] != metadata["packet_sha256"]:
                raise ValueError("Diagnostics packet binding mismatch")
            if output is not None and call.startswith("review"):
                frozen = {(assessment["label"], item["name"]): item["score"]
                          for assessment in output["assessments"] for item in assessment["dimensions"]}
                consumed = {(item["label"], item["dimension"]): item["score"] for item in row["metrics"]}
                if len(row["metrics"]) != 10 or consumed != frozen:
                    raise ValueError("Diagnostics changed the frozen judge dimensions")
            elif row["metrics"] != []:
                raise ValueError("Only completed reviews may contain judge metrics")
            safe = telemetry_metadata(metadata)
            safe["receipt_sha256"] = file_hash(path)
            safe["diagnostics_sha256"] = file_hash(diagnostics_path)
            name = f"{hypothesis}.{call}"
            prepared.append((name, safe))
            for metric in row["metrics"]:
                selected_unknown += metric["score"] is None
                if metric["score"] is not None:
                    if (metric["dimension"] not in DIMENSIONS or metric["label"] not in {"A", "B"}
                            or type(metric["score"]) not in (int, float) or metric["score"] not in (0, 1, 2)):
                        raise ValueError("Invalid diagnostic score")
                    scores[f"{name}.{metric['label']}.{metric['dimension']}"] = metric["score"]
    if not prepared:
        raise ValueError("No finished calls available for instrumentation")
    artifact_hash = digest({"calls": prepared, "scores": scores,
                            "diagnostics_sha256": file_hash(diagnostics_path)})
    root_meta = {"experiment_id": EXPERIMENT, "artifact_sha256": artifact_hash,
                 "diagnostics_sha256": file_hash(diagnostics_path),
                 "instrumented_call_count": len(prepared), "missing_call_count": len(missing),
                 "unknown_score_count": selected_unknown,
                 "source_text_logged": False, "legal_quality_established": False}
    client = langfuse_client(env_file)
    trace_id = uuid.uuid4().hex
    try:
        with client.start_as_current_observation(name="experiment-artifacts", as_type="span",
                trace_context={"trace_id": trace_id}, metadata=root_meta):
            with propagate_attributes(trace_name=EXPERIMENT, tags=[EXPERIMENT],
                    metadata={"experiment_id": EXPERIMENT, "artifact_sha256": artifact_hash}):
                for name, safe in prepared:
                    tokens = safe["token_usage"] or {}
                    usage = {dest: tokens[src] for src, dest in
                             (("input_tokens", "input"), ("output_tokens", "output")) if src in tokens}
                    cost = None if safe["price"] is None else {"total": safe["price"]}
                    with client.start_as_current_observation(name=name, as_type="generation",
                            model=safe["model"], metadata=safe,
                            input={"sha256": safe["prompt_sha256"]},
                            output={"sha256": safe["output_sha256"]},
                            usage_details=usage or None, cost_details=cost,
                            level="ERROR" if safe["status"] == "failed" else "DEFAULT"):
                        pass
        for name, value in scores.items():
            client.create_score(trace_id=trace_id, name=name, value=value, data_type="NUMERIC",
                                metadata={"experiment_id": EXPERIMENT,
                                          "source": "frozen_same_model_judgment",
                                          "human_review": False})
        client.flush()
        receipt = readback(client, trace_id, expected_hash=artifact_hash,
            score_names=set(scores), expected_scores=scores,
            expected_generations={name: safe["receipt_sha256"] for name, safe in prepared})
        receipt.update({"scope": list(hypotheses), "instrumented_calls": [name for name, _ in prepared],
                        "missing_calls": missing, "unknown_score_count": selected_unknown,
                        "completed_call_count": sum(safe["status"] == "completed" for _, safe in prepared),
                        "failed_call_count": sum(safe["status"] == "failed" for _, safe in prepared),
                        "all_ten_complete": (not missing and len(prepared) == 40 and
                            {name for name, safe in prepared if safe["status"] == "completed"} ==
                            {f"{hypothesis}.{call}" for hypothesis in HYPOTHESES for call in CALLS}),
                        "legal_quality_established": False})
        return receipt
    finally:
        client.shutdown()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("preflight", help="Authenticated local trace write/readback")
    check.add_argument("--env-file", type=Path, required=True)
    check.add_argument("--output", type=Path)
    diagnostic = sub.add_parser("diagnose", help="Run explicit local DeepEval metrics on saved artifacts")
    diagnostic.add_argument("--packets-dir", type=Path, required=True)
    diagnostic.add_argument("--run-dir", type=Path, required=True)
    diagnostic.add_argument("--output", type=Path, required=True)
    diagnostic.add_argument("--hypothesis", action="append", choices=HYPOTHESES)
    diagnostic.add_argument("--runner-snapshot", type=Path)
    emit = sub.add_parser("publish", help="Write hashes-only generation/score telemetry and read it back")
    emit.add_argument("--run-dir", type=Path, required=True)
    emit.add_argument("--diagnostics", type=Path, required=True)
    emit.add_argument("--env-file", type=Path, required=True)
    emit.add_argument("--output", type=Path, required=True)
    emit.add_argument("--hypothesis", action="append", choices=HYPOTHESES)
    emit.add_argument("--runner-snapshot", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            result = preflight(args.env_file)
        else:
            hypotheses = tuple(dict.fromkeys(args.hypothesis or HYPOTHESES))
            if args.command == "diagnose":
                result = diagnose(args.packets_dir, args.run_dir, hypotheses, args.runner_snapshot)
            else:
                result = publish(args.run_dir, args.diagnostics, args.env_file, hypotheses, args.runner_snapshot)
        if args.output:
            private_json(args.output, result)
    except Exception as exc:
        print(json.dumps({"status": "incomplete", "error_class": type(exc).__name__}),
              file=sys.stderr)
        return 2
    # Full metric rows stay private; console contains only non-reconstructive totals/receipt.
    summary = {key: value for key, value in result.items() if key not in {"rows", "missing"}}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
