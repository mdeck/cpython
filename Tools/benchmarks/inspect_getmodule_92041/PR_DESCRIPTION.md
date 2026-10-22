When `inspect.getmodule()` encounters an uncached registered frame or traceback, it currently scans `sys.modules` to populate its filename map. Resolve that case directly from the frame's globals owner when both the registered-module identity and canonical filename match, then reuse the existing filename cache.

This is the frame-path split requested in #92042. It is independent of and complementary to #156685, which removes a redundant scan during key computation. Both changes compose cleanly in either order. This PR adds 28 lines of production Python and does not include the registry watchers, C changes or negative caching from the earlier proposal.

The existing `getabsfile(module)` canonicalizer preserves source/bytecode normalization. Private execution namespaces, mismatched origins, dynamic module metadata, fileless modules and unrelated filename overrides retain the filename fallback. Existing filename-cache hits retain precedence. On an **uncached filename collision**, the verified globals owner wins over an unrelated module using the same filename; this intentional behavior is explicitly tested.

### Performance

On one current-main CPython 3.16 `-O3` Linux build, 15 interleaved fresh-process pairs per registry size, with 10,000 synthetic modules added to the ordinary registry:

| Workload | #156685 with its narrow bytecode fix | Both changes | Paired speedup, 95% CI |
|---|---:|---:|---:|
| Cold registered stack, source context enabled, depth 2 | 96.12 ms | 202.7 µs | 455.7× (433.3–482.1) |
| Newly registered filename, other filename entries warm | 2.051 ms | 5.185 µs | 393.9× (377.8–414.5) |

The bytecode fix is a separate measurement variant, not part of this PR. The exact uncorrected #156685 also shows the independent cold registered-frame gain: 87.01 ms → 4.660 µs, paired speedup 19,427.8× (18,548.4–20,458.2).

These are workload-specific synthetic measurements. Cold tests reset inspect's filename dictionaries, not the interpreter or filesystem caches. The import-like test retains other warmed entries and includes inserting/removing the target registry entry and evicting its own filename metadata. Mixed stacks containing an unregistered generated frame still require a full scan and receive no comparable benefit. We claim no steady-state stack or moduleless-miss speedup.

Eight further fresh-process crossover runs with counterbalanced within-process ABBA/BAAB batches found no meaningful regression in the tested warm paths. For the exact current replacement versus both changes: warmed frame ratio 1.002× (0.991–1.010), warmed source-context stack ratio 1.006× (0.997–1.016). Identical-code A/A controls are included in the evidence; small cross-process changes are not treated as gains.

### Validation

- 1,135 tests reported, 4 skipped; all suites pass, across inspect, zipimport support, import, linecache, traceback and pydoc; repeated successfully on the composition with the bytecode-corrected replacement.
- 648 differential cases: zero differences versus main for this candidate; the raw composition has exactly the replacement's 36 known bytecode differences, and the corrected composition has zero.
- Fresh-namespace zipimport and getsource regression check passes for all six variants.
- No existing test was removed or weakened; `git diff --check` passes.

Measurement scripts, complete raw process samples, intervals, controls, exact sources/hashes and logs: https://github.com/mdeck/cpython/tree/inspect-frame-fastpath-evidence-20261022/Tools/benchmarks/inspect_getmodule_92041.

Developed and tested with Codex (AI assistance).

<!-- gh-issue-number: gh-92041 -->
* Issue: gh-92041
<!-- /gh-issue-number -->
