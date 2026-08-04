# Draft: "I benchmarked CognoDB against 4 managed graph databases — here's what happened"

Target length: 600-900 words for a blog post, or a 6-8 tweet/LinkedIn thread.
Audience: engineers evaluating graph databases, not marketers.

## Structure

1. **Hook (2-3 sentences):** Why you did this — evaluating graph DBs is hard because
   published benchmarks are rarely apples-to-apples on hardware. State the core
   fairness rule you followed (same tier, same dataset, same queries) up front —
   this is what makes the piece credible rather than promotional.

2. **Setup, briefly:** email-Enron dataset, 5 platforms, free tiers, link to repo
   immediately so skeptical readers can check your methodology instead of taking your
   word for it.

3. **The numbers, visually:** 2-3 charts (ingest throughput, traversal p50/p95 by hop
   depth, mixed-workload throughput at 1/10/40 clients). Charts >> tables for a social
   post — tables belong in the README.

4. **The honest part:** where CognoDB won, where it didn't, and your best guess at
   *why* (architecture, not marketing copy). If CognoDB loses on some metric, say so —
   this is the section that actually earns engineering credibility and, per the
   assignment's own evaluation criteria, is explicitly graded on honesty.

5. **Caveats, in the open:** free-tier throttling, resource-parity limits, anything
   that went wrong during the run. Two sentences, not buried.

6. **Close:** link to the repo, invite people to re-run it and report back.

## Notes

- Do not claim a platform "wins" as a headline — the assignment explicitly grades on
  fairness, not on a winner.
- Real numbers only. Fill this in after `src/stats.py` output is in the README.
