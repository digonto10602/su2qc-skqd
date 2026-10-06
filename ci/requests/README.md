# ci/requests/ — one file per CI job request (prompts/33 section 7c)

Written ONLY by `scripts/ci_request.sh TOKEN [TOKEN ...]` (one commit for all tokens of one call):
`<NNN>-<TOKEN>.txt`, first non-comment line = the token, then a `# requested ... nonce ...` comment.

The concurrent poller (`ci/poll_concurrent.sh`, once the owner has installed it on Perlmutter) reads
every `*.txt` here in file-name order, identifies each request as `<path>@<commit that last touched
it>`, and runs each identity once (consumed identities are kept in `~/skqd-ci/consumed` on
Perlmutter), up to `MAX_CONCURRENT` jobs at a time and `MAX_JOBS_PER_DAY` per UTC day; unknown
tokens are refused and reported in `ci/status/<TOKEN>.json`.  `scripts/ci_check.sh` lists the state
of every request.  The one-job poller installed before prompts/33 ignores this directory and reads
only `ci/request.txt` (`scripts/ci_request.sh --legacy TOKEN`).

This README is not a request (only `*.txt` files are).  Never edit or delete a request file by hand:
a new commit touching a file is a new request.
