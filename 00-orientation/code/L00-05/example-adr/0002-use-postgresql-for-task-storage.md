# ADR-0002: Use PostgreSQL for task storage

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

Task-এর data relational (user → project → task), transaction দরকার (একসাথে task তৈরি ও counter আপডেট), এবং team-এর SQL অভিজ্ঞতা আছে।

## Options considered

1. **PostgreSQL** — ACID transaction, শক্তিশালী index ও query planner, বিস্তৃত tooling। অসুবিধা: আলাদা server চালাতে ও backup নিতে হয়।
2. **SQLite** — কোনো server নেই, খুব সহজ। অসুবিধা: একাধিক app instance থেকে একসাথে লেখা সীমিত।
3. **MongoDB** — flexible schema। অসুবিধা: এই data-র গঠন relational, তাই সুবিধা কম।

## Decision

PostgreSQL ব্যবহার হবে। Local development-এ container-এ, production-এ managed service বিবেচনা করা হবে।

## Consequences

- ইতিবাচক: transaction ও constraint দিয়ে data সঠিকতা।
- নেতিবাচক: backup, upgrade ও connection pooling-এর operational দায়িত্ব।
- পুনর্বিবেচনা: write load একটি server-এর সীমা ছাড়ালে।
