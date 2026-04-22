# test_coverage_count — falsify self-claim

Asserts the falsify test suite has more than 400 distinct
unittest test methods across `tests/test_*.py`.

**Why the threshold matters.** Test-method count is a crude but
honest proxy for coverage breadth; a sustained drop below 400
indicates tests were deleted without replacement. The lock
prevents the threshold from being silently lowered when someone
rips out a batch of tests in a refactor.

**How the metric is computed.** `metric.py` parses every
`test_*.py` under `tests/` with `ast`, counts function
definitions whose name starts with `test_`, and returns
`(total_tests, n_files_scanned)`. Stdlib only.
