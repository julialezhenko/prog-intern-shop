# CommerceLab Future Backlog

Ideas that are deliberately **not** part of the MVP and not yet assigned as internship tasks. The active
specialist tasks live in `docs/internship-tasks.md` (and in the LMS). Items below can become new tasks.

## Backend

1. Guest carts (session-based) merged into the customer cart on login.
2. Multi-warehouse split fulfilment and allocation policy configuration.
3. Product image uploads (`ImageField` + storage) replacing URL-only images.
4. Gift cards with ledger-based balances and redemption history.
5. Loyalty points with earn, redeem, expiry and adjustment events.
6. Multi-currency price lists and exchange-rate snapshots.
7. Abandoned-cart notification scheduling through Celery.
8. Delivery tracking and shipment-provider webhook simulation.
9. Full-text product search (PostgreSQL `SearchVector`) with ranking.

## Frontend

10. Product comparison.
11. Transfer creation, dispatch and receipt screens for warehouse staff.
12. Campaign performance and funnel visualisations inside the admin.
13. Bulk catalog CSV import with validation preview.
14. Customer support order/return timeline.

## QA

15. OpenAPI contract fuzzing in CI.
16. Visual-regression baselines for responsive storefront breakpoints.
17. Chaos tests for payment timeouts and duplicate callbacks.
18. Migration upgrade tests from tagged releases.
19. Accessibility conformance regression checks.

## Analytics

20. Promotion incrementality and cannibalisation analysis.
21. Product recommendation evaluation (offline metrics).
22. Price elasticity using `PriceHistory` and funnel events.
23. Scheduled executive reports with freshness checks.
24. Fraud-pattern labels and explainable score monitoring.

## DevOps

25. Redis caching with measurable catalog hit-rate targets.
26. Celery workers, beat schedules and dead-letter guidance.
27. PostgreSQL backups, restore drill and anonymised fixtures.
28. Observability dashboards for latency, errors and queue depth.
29. Staging deployment, secret management and dependency scanning.

## Product

30. Recommendation-engine experiments and consent boundaries.
31. A/B testing assignment and exposure-event contracts.
32. Dynamic pricing guardrails and approval workflow.
33. Marketplace seller onboarding and commission model.
34. Subscription/replenishment orders.
