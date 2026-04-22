# cli_startup — falsify self-claim

Asserts the falsify CLI starts in under 500ms median over 5
back-to-back invocations of `python3 falsify.py --help`.

**Why the threshold matters.** Startup is a human-facing cost: the
commit-msg hook runs `falsify guard` on every commit, and the
pre-commit framework calls `falsify doctor`. If startup climbs
past half a second, the tool becomes annoying to adopt.

**How the metric is computed.** `metric.py` times
`subprocess.run([sys.executable, "falsify.py", "--help"])` five
times with `time.perf_counter()` around each call, then returns
the median in milliseconds. Stdlib only.
