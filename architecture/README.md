# Architecture

এই folder-এ থাকবে:

| বিষয় | Path |
|---|---|
| Architecture Decision Records (repository ও project-স্তরের) | `adr/` |
| Continuous project-এর প্রতিটি ধাপের architecture | [continuous-project-evolution.md](continuous-project-evolution.md) |
| Capstone architecture | Project 13-এর `docs/` |

## Diagram-এর নিয়ম

- Text-ভিত্তিক diagram (ASCII বা Mermaid), যাতে Git-এ diff দেখা যায়।
- প্রতিটি diagram-এ: component, data flow-এর দিক, trust boundary, এবং কোথায় কী ব্যর্থ হতে পারে।
- C4 model-এর স্তর: Context → Container → Component (L00-05-এ শেখানো হবে)।

## ADR

- [adr/0001-repository-structure-and-primary-os.md](adr/0001-repository-structure-and-primary-os.md)
