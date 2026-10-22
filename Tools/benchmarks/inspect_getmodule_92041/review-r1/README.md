# Review revision validation — 2026-10-22

Revision: ef27738a6fea5551f4176e370ba5b3c0a63dd5da; parent: bda170b70b98398fa0d14abc0a190beb8efaee13.

Removes the blanket module `__getattr__` exclusion while retaining the stored-string filename and exact-module checks; applies readability feedback and documents lookup-history-dependent filename collisions.

## Correctness

- Six suites pass: 1,138 reported tests, four skipped (inspect, zipimport_support, import, linecache, traceback, pydoc).
- The new static-filename/module-hook no-scan test fails on the parent for the expected registry scan and passes on the revision.
- 150 repeated dynamic filename, dynamic loader and module-subclass tests pass on each of parent and revision.
- All 16 frame-owner regression methods pass composed with the bytecode-corrected replacement.
- 648 differential cases: revised candidate zero differences from main; raw replacement and raw composition retain the same 36 bytecode differences; corrected replacement and corrected composition have zero.
- Fresh-namespace zipimport/getsource checks pass for all six variants.
- sphinx-lint 1.0.2 with default-role enabled and git diff --check pass.
- Existing filename cache-hit instruction prefix is identical; see cached-prefix.log.

## Targeted performance recheck

Same native CPython 3.16 -O3 build and synthetic 10,000-module registry as the original evidence. Source snapshots are in variants/before.py and variants/after.py. These measurements compare this PR before and after review edits, rather than repeating the original replacement-versus-composition comparison.

Eight fresh processes, four counterbalanced ABBA/BAAB rounds per workload and pair, minimum 30 ms calibrated batches, pinned to the highest allowed CPU, hash seed zero, GC disabled. Before/before_control imports identical source under distinct names. All raw samples are retained. A second, pre-publication run used 16 fresh processes and eight rounds for the two warm paths because the first warm-stack interval was too wide. Both runs are retained; the second run supplies the warm conclusions. Intervals use 20,000 bootstrap resamples over process-level mean log ratios, not over dependent batches.

| Workload | Before/after speed ratio | 95% bootstrap interval |
|---|---:|---:|
| cold_stack | 1.0060 | 0.9971–1.0143 |
| incremental_frame | 0.9982 | 0.9864–1.0103 |
| registered_frame | 0.9922 | 0.9806–1.0040 |
| stack_depth2_context1 | 0.9990 | 0.9863–1.0111 |

There is no statistically resolved change in these workloads. The refined warm intervals allow approximately a 2% frame regression or 1.4% stack regression at their lower endpoints; smaller effects are unresolved. No additional performance gain is claimed for these revisions. The cold recheck supports retaining the original optimization result, whose much larger baseline matrix remains separately pinned in the parent evidence. The global median timings need not have the same ratio as the process-paired estimate.

## Reproduction

The frozen measured sources are stored as `variants/*.py.txt` so repository tooling does not treat them as maintained Tools scripts. Their bytes and the hashes below are unchanged. Before running the scripts, materialize executable copies from this directory:

```sh
python -c "from pathlib import Path; [p.with_suffix('').write_bytes(p.read_bytes()) for p in Path('variants').glob('*.py.txt')]"
```

The hash table names the resulting `.py` files. Run review_crossover.py and warm_refined.py with the built native interpreter. Run analyze_crossover.py and analyze_refined.py using Python with NumPy. They read/write the JSON files beside these scripts. Correctness scripts use the six variant snapshots and the PR test file; run verify_review.py from a checkout of the revision. The corrected replacement remains a measurement variant outside this PR.

## Snapshot SHA-256

- `after.py`: `98b004be6e5b1fa01884bfc5714e3b15f5a02424b6ff5f5e393abd60c3c13a6c`
- `before.py`: `1ade97d06f56acf22a1e15894703403020d9f9978a9c6e77646f931dca8e030f`
- `candidate.py`: `98b004be6e5b1fa01884bfc5714e3b15f5a02424b6ff5f5e393abd60c3c13a6c`
- `combined.py`: `dbbbf45348faddbba6ebfb05c16cee0bc12a3fc2b23e5ce3e867507fe903d14b`
- `combined_fixed.py`: `7d22a1c960812dc5b52b185c5cc3d836d9f16befc23cabaae3df750054ecbccf`
- `main.py`: `b54b017cf6db8876a7e80ad10672878b6427ad8824093b39fbf18af7e3ed33c4`
- `replacement.py`: `e3dc4310305e12fc0535c1da1dfbdb98064d5aaeab6d293399ab7fccac5d9a3b`
- `replacement_fixed.py`: `052aac914791f645e7f111bc25c14c1c3f855fc96b3f21e23c5b9b323943d34f`
