# Engine 2 hotfix

Fixes:
- unrelated official central-bank announcements no longer count as instrument-relevant;
- official-source reliability no longer automatically means high market impact;
- GDELT HTTP 429 responses use bounded exponential backoff and `Retry-After`;
- default GDELT request size reduced from 75 to 30 records.
