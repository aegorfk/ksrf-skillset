#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="${CODEX_HOME:-$HOME/.codex}/skills"
target_dir="$repo_dir/skills"

if [[ ! -d "$source_dir" ]]; then
  echo "Global Codex skills directory does not exist: $source_dir" >&2
  exit 1
fi

mkdir -p "$target_dir"

skill_names=(
  ksrf-argument-patterns
  ksrf-case-triage
  ksrf-cassation-judicial-meaning
  ksrf-complaint-cycle
  ksrf-complaint-facts-demands
  ksrf-complaint-qa
  ksrf-court-request-motion
  ksrf-decision-execution
  ksrf-echr-argumentation
  ksrf-exhaustion-planner
  ksrf-explore-arguments
  ksrf-formal-filing-check
  ksrf-practice-authority-builder
  ksrf-rights-argument-builder
)

for skill_name in "${skill_names[@]}"; do
  skill_dir="$source_dir/$skill_name"
  [[ -d "$skill_dir" ]] || {
    echo "Required canonical skill is missing: $skill_dir" >&2
    exit 1
  }
  rsync -a --delete --delete-excluded \
    --exclude='.DS_Store' \
    --exclude='.git/' \
    --exclude='.serena/' \
    --exclude='.pytest_cache/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='credentials.json' \
    --exclude='secrets.json' \
    --exclude='token.json' \
    --exclude='id_rsa' \
    --exclude='id_ed25519' \
    --exclude='*.pem' \
    --exclude='*.p12' \
    --exclude='*.pfx' \
    --exclude='*.key' \
    "$skill_dir/" "$target_dir/$skill_name/"
done

argument_scripts="$source_dir/ksrf-argument-patterns/scripts"
for tool_name in \
  build_constitutionalist_authority_corpus.py \
  enrich_ksrf_argument_patterns.py \
  extract_ksrf_argument_patterns.py; do
  if [[ -f "$argument_scripts/$tool_name" ]]; then
    cp "$argument_scripts/$tool_name" "$repo_dir/tools/$tool_name"
  fi
done

echo "Synced global KSRF skills into $target_dir"
