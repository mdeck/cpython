# CPython inspect.getmodule: focused follow-up assessment

**Recommendation: prepare a separate PR for uncached registered frames and tracebacks.** The opportunity is substantial for registered filename-cache misses, survives composition with #156685, and needs 28 added lines of production Python. It does not solve repeated moduleless misses. Do not revive the C watcher/negative-cache portion in this PR.

The prepared code is [on the review branch](https://github.com/mdeck/cpython/tree/inspect-registered-frame-fastpath-20261022); [review the full diff](https://github.com/mdeck/cpython/compare/97d361116f27d9a53ff735151ba26f5bcb463b74...inspect-registered-frame-fastpath-20261022). Final head: `6c72434f0e04c950a3908ebf40b1b5d27f64c72a`. No upstream PR was opened. CPython requires the human author to review AI-assisted changes before proposing them as a PR.

## Opportunity and implementation

On an existing filename-cache hit, execute the existing path. On a miss, a frame or traceback can establish module ownership by checking its globals against the exact module object registered under `__name__`, then comparing the already computed query filename with `getabsfile(module)`. A successful lookup adds that filename to the existing cache. Otherwise the original full filename scan remains available.

The canonicalizer is deliberately retained: bypassing `.pyc` to `.py` normalization was the regression identified in both previous proposals. Module subclasses, module `__getattr__`, invalid metadata, fileless modules, mismatched execution origins and unrelated private filename overrides retain the fallback.

One intentional compatibility detail requires author/maintainer review: **on an uncached filename collision, the verified globals owner wins over an unrelated registered module using the same filename**. An existing filename-cache entry retains its previous precedence. This is tested and must be disclosed; the 648-case matrix below does not include this intentional collision rule.

## Relationship to #156685

No dependency is needed. Base the PR directly on current `main`, acknowledge #156685, and keep its bytecode correction outside this PR. #156685 changes filename-key computation before lookup; this proposal changes resolution after a cache miss. Three-way merges in both orders were conflict-free and byte-identical to the explicitly composed implementation. The test additions are in `test_inspect`; #156685 adds its zipimport test in a different file, and the NEWS files differ.

This implements the frame-path split requested in [the August 30 review](https://github.com/python/cpython/pull/92042#issuecomment-5471184245), without the old registry watchers, C changes, private `_imp` API, broad negative cache or its mutation tradeoffs.

## Results beyond the replacement

The baseline in this table is #156685 **with the narrow bytecode normalization correction described in its review**; that correction is a separate benchmark variant and is not in our prepared PR. The tested workloads use ordinary `.py` filenames, so the bytecode fix does not account for these gains.

| Added modules | Workload | Baseline median | Candidate median | Paired speedup (95% CI) |
|---:|---|---:|---:|---:|
| 1,000 | Cold registered stack, depth 2, source context enabled | 10.500 ms | 214.263 µs | 49.8× (46.3–54.3) |
| 1,000 | New registered filename, other cache entries warm | 245.355 µs | 5.463 µs | 43.2× (40.9–45.6) |
| 10,000 | Cold registered stack, depth 2, source context enabled | 96.118 ms | 202.671 µs | 455.7× (433.3–482.1) |
| 10,000 | New registered filename, other cache entries warm | 2.051 ms | 5.185 µs | 393.9× (377.8–414.5) |

For comparison, the independent candidate on unchanged current main:

| Added modules | Workload | Baseline median | Candidate median | Paired speedup (95% CI) |
|---:|---|---:|---:|---:|
| 1,000 | Cold registered stack, depth 2, source context enabled | 10.613 ms | 222.236 µs | 48.1× (44.3–52.0) |
| 1,000 | New registered filename, other cache entries warm | 239.625 µs | 9.663 µs | 25.3× (24.1–26.9) |
| 10,000 | Cold registered stack, depth 2, source context enabled | 94.377 ms | 203.203 µs | 452.1× (436.4–469.6) |
| 10,000 | New registered filename, other cache entries warm | 2.125 ms | 9.062 µs | 226.0× (218.7–232.8) |

The isolated cold-frame case, including the exact uncorrected replacement:

| Added modules | Workload | Baseline median | Candidate median | Paired speedup (95% CI) |
|---:|---|---:|---:|---:|
| 1,000 | Cold registered frame lookup | 9.758 ms | 4.686 µs | 1988.7× (1828.1–2137.7) |
| 10,000 | Cold registered frame lookup | 87.011 ms | 4.660 µs | 19427.8× (18548.4–20458.2) |

These are controlled synthetic workloads, not application-wide speedups. “Cold” clears inspect's filename dictionaries while retaining a warm interpreter, linecache and filesystem caches. Registry sizes add the stated number of synthetic modules with distinct __file__ paths to the normal registry. The import-like case inserts a registered module and removes only its own filename/metadata cache entries, retaining all other warm entries; this reproduces a new filename without unbounded registry growth and includes its setup/teardown cost. Stack depths count recursive workload calls; the harness contributes additional frames.

## Limits and negative results

Warm positive cache hits execute the existing lookup path; we do not claim a steady-state gain. Mixed stacks containing an unregistered generated frame still require the filename fallback. At 10,000 added modules, their cold captures remained about 95–103 ms and their warm captures about 6.4–6.6 ms. The large registered-stack improvement does not generalize to these mixed stacks. Repeated bare-code misses and registry-churn misses likewise remain outside this proposal's optimization.

The initial cross-process run's identical-code A/A control produced apparent small changes, including some bootstrap intervals excluding 1. Therefore its intervals are conditional estimates and do not capture all process/layout/host bias. The large cold gains are far outside that control variation; small warm differences were investigated separately with the crossover below rather than labeled improvements or regressions.

## Correctness and regression checks

- Final candidate: all six suites pass, 1,135 tests run, 4 skipped.
- Candidate composed with the corrected replacement: the same 1,135 tests reported, 4 skipped; all suites pass.
- Suites: inspect, zipimport support, import, linecache, traceback and pydoc. Final runs are sequential to avoid a temporary-file collision observed in an earlier parallel run.
- 648 differential cases span frames, tracebacks and code objects; `.py`, `.pyc` and other filenames; source present/absent; loaders; registered/private globals; and filename overrides. Standalone candidate: zero differences from main. Uncorrected replacement: 36 differences; uncorrected composition: the same 36. Bytecode-corrected replacement and composition: zero differences.
- A separate fresh-namespace zipimport/getsource regression check passes for all six variants.
- Added tests cover independent cold frame/traceback resolution, no registry scan, duplicate filenames, cache precedence, metadata changes, private globals, wrong origins, explicit overrides, fileless modules, same-name replacement, module subclasses and sourceless/bytecode imports.
- No existing tests were removed or weakened. `git diff --check` passes.

Validation here is Linux release-build validation, not a claim of Windows/macOS, debug, sanitizer, or free-threaded CI coverage.

## Measurement protocol

Current main: `97d361116f27d9a53ff735151ba26f5bcb463b74`; replacement head: `03df224b0164352e784baaa962c8e41735b7121f`. The replacement's two-line production change was applied to this fixed current main. All Python variants run on the **same freshly built CPython 3.16 interpreter**, GCC 13.3.0, `-O3`, no PGO/LTO. This avoids unrelated native build differences.

Primary matrix: 7 variant/control configurations × 15 fresh processes × 2 registry sizes = 210 processes. Public-stack/import-like matrix: 5 configurations × 15 × 2 = 150 processes. Variant order rotates each repetition; each process pins to CPU 8, warms specialization/core execution, disables GC for timing, and uses `PYTHONHASHSEED=0`. Each sample is the median of three batches after calibration to at least 30 ms. No builds or tests ran during the retained timing runs. Cgroup throttling counters did not increase during the two main matrices.

Speedup estimates are geometric means of matched round-by-round baseline/candidate ratios. 95% intervals use 20,000 paired bootstrap resamples of independent-process pairs, with a fixed RNG seed. Timing columns are medians, so dividing the two columns need not reproduce the paired estimate exactly. The machine is a virtualized AMD EPYC 9V74 environment, not a frequency-isolated physical benchmark host. Raw process samples, scripts, hashes, logs and all statistics accompany this report.

## Warm crossover

Eight fresh processes load the compared variants in randomized order. Each process performs eight counterbalanced ABBA/BAAB rounds for function lookup, warmed registered-frame lookup and warmed stack capture with source context. Caches are warmed before the crossed batches. Comparisons use 10,000 added synthetic modules; no other tests or builds ran during the retained crossover. Intervals bootstrap the eight process-cluster mean log ratios, not the 64 rounds as if they were independent.

| Baseline → candidate | Workload | Paired speedup (95% CI) |
|---|---|---:|
| replacement → combined | function | 1.002× (0.992–1.011) |
| replacement → combined | registered_frame | 1.002× (0.991–1.010) |
| replacement → combined | stack_depth2_context1 | 1.006× (0.997–1.016) |
| replacement_fixed → combined_fixed | function | 1.029× (1.015–1.049) |
| replacement_fixed → combined_fixed | registered_frame | 1.003× (0.975–1.026) |
| replacement_fixed → combined_fixed | stack_depth2_context1 | 1.014× (0.985–1.062) |
| replacement_fixed → replacement_fixed_control | function | 1.029× (1.009–1.055) |
| replacement_fixed → replacement_fixed_control | registered_frame | 0.997× (0.986–1.007) |
| replacement_fixed → replacement_fixed_control | stack_depth2_context1 | 0.998× (0.980–1.018) |

The current replacement versus its composition shows no meaningful warmed frame/stack regression: the confidence intervals exclude a 2% slowdown on those specific workloads. The corrected-replacement comparisons exclude a 5% slowdown for the tested warm paths. The apparent ~2.9% function gain in the fixed comparison is also present in its identical-code control, so it is not credited to this patch. No general speedup or universal no-regression claim follows from these measurements.

## Submission readiness

The implementation, tests, NEWS entry, reproducible benchmarks and proposed PR text are prepared. Open a **new independent PR**, not a reopening or force-push of #92042, after the human author reviews the focused diff and understands the collision rule. [CPython's AI policy](https://devguide.python.org/getting-started/ai-tools/) requires this review before submission. AI assistance is disclosed in the commit and proposed description.

## Reproduce

Check out this evidence branch, build its CPython interpreter, then run the following from this directory:

```sh
/path/to/built/cpython/python reproduce.py
python3 analyze_benchmarks.py
python3 analyze_crossover.py
```

`reproduce.py --prepare-only` reconstructs the exact main/candidate and composed Python variants without running the benchmarks. Full timing reproduction takes several minutes. The raw JSON files preserve per-process samples; `source-sha256.txt` verifies the six compared `inspect.py` variants. NumPy is required only for the two statistical-analysis scripts; use an interpreter with NumPy for those scripts.
