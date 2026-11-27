# Log

Append only. Newest entry last. Format per entry:

## <YYYY-MM-DD HH:MM> <one-line title>
- Tried: <>
- Learned: <>
- Dead ends: <>
- Decision: <iterate | pivot | harden | stop | none yet>
- Next question: <>
- Later: <ideas parked, out of scope for now>

## 2026-11-25 18:30 PoC started
- Tried: nothing yet
- Learned: nothing yet
- Dead ends: none
- Decision: none yet
- Next question: none yet
- Later: none

## 2026-11-25 19:30 Signature verified
- Tried: ran ./verify.sh against the provider's test vector
- Learned: ./verify.sh exits 0, the HMAC over the raw body matches
- Dead ends: parsing JSON before hashing changed the bytes
- Decision: none yet
- Next question: does the header carry hex or base64 in production?
- Later: retries
