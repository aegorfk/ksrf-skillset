## Context

The validator receives data directly from `json.loads`, so any field can hold
any JSON value even when the documented artifact contract expects a string or
an array of string identifiers. The current implementation applies `set()`,
set membership, and `sorted()` before checking those types. JSON arrays and
objects are unhashable, `null` and numbers can be non-iterable, and mixed
scalar sets are not orderable on current Python versions.

## Goals / Non-Goals

- Goals:
  - return a deterministic list of errors for every JSON-derived root value;
  - name the exact field or array index responsible for a type violation;
  - continue checking independent fields after malformed values;
  - keep valid artifacts and CLI read/syntax behavior unchanged;
  - prove source and clean-installed parity.
- Non-Goals:
  - introduce JSON Schema or a new runtime dependency;
  - silently coerce scalars, objects, or `null` into identifier strings/lists;
  - redesign the full artifact contract or make optional fields required;
  - infer missing identifiers, deduplicate user data, or authorize promotion;
  - change the validator's established stdout/stderr channels.

## Decisions

### Normalize only validated reference identifiers

A small helper receives a container, field name, diagnostic path, and shared
error list. Missing optional reference arrays retain the existing empty-array
default. A present non-array value yields one `must be an array` error. Each
array entry that is not a non-empty string yields an indexed error. Only valid
string identifiers enter the returned set, so difference and sorting
operations are safe and deterministic.

This is validation, not coercion: a number such as `7` never becomes `"7"`,
and an object is never stringified for comparison.

### Guard enum and principal membership

Enum membership is attempted only for strings. Every other JSON type follows
the existing field-specific invalid-value diagnostic instead of reaching set
membership. `principal_hypothesis_id` remains nullable; a non-null non-string
value receives a type diagnostic and does not enter hypothesis-set membership.
The separate human-approval rule remains evaluated from the original non-null
value so an invalid principal cannot bypass that gate.

### Preserve error order and CLI channels

Errors remain appended in document traversal order: root/container errors,
finding errors, hypothesis errors, then portfolio errors. Indexed array-type
errors precede unknown-reference errors derived from valid entries in that
array. Unknown identifiers are sorted as strings.

Semantic invalidity returns code `1` and prints `ERROR:` lines to stdout. The
former one-off non-object-root stderr branch is normalized into that semantic
channel. Filesystem errors, invalid UTF-8, JSON syntax errors, and bounded
decoder failures such as excessive nesting or the interpreter's integer-digit
limit return code `2` on stderr. The read/decode block catches `OSError`,
`ValueError`, and `RecursionError`; it does not catch process-control or memory
failures. A valid artifact retains its exact success line and code `0`. No
traceback is emitted for any JSON-derived root value.

### Render reflected identifiers without changing comparison values

Duplicate-ID diagnostics are the only errors that interpolate an identifier
directly. They render the string as an ASCII-safe escaped JSON fragment, with
outer quotes removed to preserve the ordinary ASCII diagnostic. Comparison and
storage continue to use the original string. This keeps lone surrogates,
newlines, quotes, backslashes, and control characters single-line and encodable
without treating an escaped display value as the actual identifier.

## Risks / Trade-offs

- Malformed arrays may now produce more than one useful error because checking
  continues; this is intentional and deterministic.
- Some invalid scalar references receive a more precise type message than the
  former generic unknown-reference message. Valid inputs and outputs are
  unchanged.
- Totality is limited to JSON-derived values. Arbitrary custom Python objects
  supplied by an in-process caller are outside the public contract.

## Verification

First, regression tests reproduce each current exception family: a non-object
root, non-iterable
reference containers, unhashable entries, mixed sortable types, unhashable
enum values, an unhashable principal reference, and duplicate identifiers with
a lone surrogate, invalid UTF-8, excessive nesting, and an overlong integer
where the interpreter enforces a digit limit. The green tests require
addressed errors and no exception for all JSON value kinds at every unsafe
field family. Source and clean-installed CLI tests require code `1`, empty
stderr, no `Traceback`, deterministic `ERROR:` output, and unchanged input.
A valid control retains its byte-exact success response. Full root/skill,
strict source/runtime, OpenSpec, offline, manifest, clean-install, independent
review, publication, and installed-current checks remain release gates.
