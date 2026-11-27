# POC: Fixture webhook check

Started: 2026-11-25 18:30 | Timebox (first pass): 2 hours | Tier: 1 | Deal: none | Repo visibility: private

## Question
Can a small receiver verify an HMAC signature?

## Success check
`docker compose up` starts all six services and the gateway answers on port 8080.

## Assumptions and risks (riskiest first)
1. The signature must be computed over the raw body.
2.
3.

## In scope
- HMAC check

## Out of scope
- Persistence

## Manual check (only if verify.sh cannot do it)
none
