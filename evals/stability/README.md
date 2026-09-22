# Decision stability benchmark

This benchmark is an opt-in, live-only measurement of repeated calls for a
small fixed set of public cases. It is not run by normal CI and requires
`TYPESAFE_API_KEY` in the process environment:

```bash
TYPESAFE_API_KEY="..." \
  python scripts/run_stability_benchmark.py --live --repeats 3
```

For every case, the runner reports:

- `probability_mean`: mean of the per-invocation probability means;
- `probability_std`: population standard deviation across those invocation means;
- `probability_range`: maximum minus minimum invocation mean;
- `mean_absolute_delta`: mean absolute delta between adjacent invocation means;
- `decision_consistency`: fraction of repeats matching the first selected decision.

For multi-answer tools such as `verify`, `gate`, `review`, and `evaluate`, each
invocation is reduced to one mean before the repeat statistics are calculated.
This prevents different claims or checks within one case from being mistaken
for repeated-call instability.

The top-level `global_probability_distribution` is retained only as a
descriptive distribution of raw probabilities pooled across cases. It is not a
stability metric. The top-level case metrics are the appropriate values for
comparing repeat behavior.
