# Implementation Backlog: Stripe Connect Risk Accounting

Дата: 2026-04-21
Статус: Draft v1
Источник: `Specifications/stripe-connect-risk-architecture.md`

## Phase 0. Foundation Alignment

### Цель

Подтвердить границы первой версии и убрать архитектурную неопределенность до начала кодинга.

### Deliverables

- утвержденный scope v1;
- согласованные currencies для запуска;
- подтвержденный refund policy baseline;
- подтвержденный Stripe Connect onboarding mode;
- подтвержденная policy блокировки и top-up.

### Tasks

- зафиксировать список валют v1;
- выбрать стратегию service fee:
  - отдельная строка;
  - или внутренняя компонента gross amount;
- определить, кто оплачивает Stripe processing cost по умолчанию;
- определить default credit limit per currency;
- определить thresholds warning/block;
- определить default reserve policy.

### Exit criteria

- все money rules подтверждены;
- нет открытых вопросов, блокирующих DB design.

## Phase 1. Database and Schema

### Цель

Ввести storage model для wallets, ledger, refund cases и risk policies.

### Deliverables

- SQLAlchemy models;
- Alembic migrations;
- backward-compatible schema upgrade.

### Tasks

- добавить `agent_wallets`;
- добавить `agent_risk_policies`;
- добавить `agent_ledger_entries`;
- добавить `refund_cases`;
- расширить `agents`;
- расширить `orders`;
- добавить indexes по:
  - `agent_id`
  - `currency`
  - `created_at`
  - `status`
  - `order_id`
- написать миграции;
- добавить migration tests.

### Exit criteria

- миграция применяется на чистой и существующей БД;
- schema поддерживает multi-currency wallets.

## Phase 2. Domain Services

### Цель

Собрать core business logic в изолированных сервисах.

### Deliverables

- `wallet_service`
- `ledger_service`
- `risk_policy_service`
- `refund_calculation_service`
- `payout_calculation_service`

### Tasks

- реализовать posting API для ledger;
- реализовать wallet recompute logic;
- реализовать threshold evaluation;
- реализовать risk capacity calculation;
- реализовать top-up allocation logic;
- реализовать helper для counting refund events in window;
- реализовать idempotency rules для postings.

### Exit criteria

- любой sale/refund/top-up может быть отражен как набор ledger postings;
- wallet может быть восстановлен из ledger.

## Phase 3. Stripe Connect Integration

### Цель

Расширить текущий Stripe flow до Connect + destination charges.

### Deliverables

- connected account onboarding endpoints;
- agent payment mode `stripe_connect`;
- connect-aware checkout session creation;
- Stripe webhook pipeline.

### Tasks

- добавить account creation endpoint;
- добавить onboarding link endpoint;
- добавить account status refresh endpoint;
- обновить `create-session` под destination charges;
- сохранить Stripe IDs в orders;
- добавить webhook endpoint:
  - `checkout.session.completed`
  - `payment_intent.payment_failed`
  - `charge.refunded`
  - `charge.dispute.created`
  - `account.updated`
- добавить signature verification;
- добавить idempotent webhook processing.

### Exit criteria

- один агент может пройти onboarding;
- checkout создается через Connect;
- webhook подтверждает оплату и приводит order к paid state.

## Phase 4. Sale Accounting

### Цель

Автоматически отражать каждую успешную продажу в ledger и wallet.

### Deliverables

- sale posting pipeline;
- reserve hold logic;
- status recomputation on sale.

### Tasks

- на `checkout.session.completed` создавать:
  - `sale_credit`
  - `platform_fee_credit`
  - `processing_fee_debit`
  - `reserve_hold`
- обновлять wallet и thresholds;
- логировать status transitions;
- написать tests на multi-currency sale posting.

### Exit criteria

- после оплаты у агента корректно меняется balance;
- payouts можно считать только из ledger.

## Phase 5. Refund Engine

### Цель

Сделать refund управляемым, просчитываемым и безопасным для платформы.

### Deliverables

- `refund/calculate`;
- `refund/execute`;
- `refund_case` lifecycle;
- agent debit posting logic.

### Tasks

- реализовать pre-calculation endpoint;
- рассчитывать:
  - customer refund amount
  - platform cost amount
  - agent debit amount
  - post-refund status
- при execute:
  - вызывать Stripe refund
  - записывать refund_case
  - создавать ledger postings
  - обновлять wallet/status
- поддержать modes:
  - `full_refund`
  - `ticket_only_refund`
  - `custom_partial_refund`

### Exit criteria

- refund нельзя выполнить без calculation step;
- любой refund оставляет auditable trace.

## Phase 6. Risk Engine and Enforcement

### Цель

Включить warnings, restrictions, autoblock и top-up logic.

### Deliverables

- status machine;
- autoblock rules;
- manual override support;
- top-up handling.

### Tasks

- реализовать evaluation by money threshold;
- реализовать evaluation by event threshold;
- блокировать checkout creation для blocked agents;
- блокировать payout creation для blocked agents;
- реализовать top-up endpoint;
- реализовать auto-unblock eligibility check;
- добавить manual force block / manual release.

### Exit criteria

- blocked agent не может продавать;
- топ-ап меняет exposure и может разблокировать агента;
- warnings и blocks объяснимы через audit trail.

## Phase 7. Admin Panel

### Цель

Дать super admin и платформе полное управление риском и агентами.

### Deliverables

- global risk settings screen;
- agent wallet screen;
- agent ledger screen;
- refund calculation UI;
- top-up UI;
- block/unblock UI.

### Tasks

- добавить страницу `Risk Settings`;
- добавить формы global defaults;
- добавить секцию wallet в agent details;
- добавить таблицу ledger;
- добавить risk incidents view;
- добавить refund preview UI;
- добавить top-up modal;
- добавить block reason and unblock reason flows.

### Exit criteria

- super admin может менять thresholds без DB вмешательства;
- агентский риск виден в UI в реальном времени.

## Phase 8. Monitoring and Operations

### Цель

Сделать постоянный программный контроль каждой транзакции и дрейфа данных.

### Deliverables

- reconciliation jobs;
- risk alerts;
- operational dashboards;
- incident logs.

### Tasks

- hourly wallet reconciliation;
- daily ledger integrity verification;
- daily blocked agents report;
- alert on:
  - negative exposure threshold reached
  - block threshold reached
  - refund without reverse transfer
  - webhook processing failure
  - payout attempted for blocked agent
  - Stripe vs DB mismatch
- сохранить alerts в DB или structured logs.

### Exit criteria

- платформа получает сигнал о риске до накопления silent losses;
- любой drift поднимает alert.

## Phase 9. Shadow Mode Rollout

### Цель

Проверить correctness без влияния на боевые продажи.

### Deliverables

- shadow calculations;
- comparison reports;
- dry-run alerts.

### Tasks

- считать wallets и statuses в фоне;
- не блокировать агентов;
- сравнивать ledger-based payoutable с текущей моделью;
- собирать ошибки расчета;
- валидировать thresholds на реальных данных.

### Exit criteria

- расчеты совпадают с ожиданием;
- нет критичных расхождений.

## Phase 10. Controlled Launch

### Цель

Включить систему на одном агенте с реальным контролем риска.

### Deliverables

- test agent activation;
- end-to-end sale/refund/top-up validation;
- operational playbook.

### Tasks

- выбрать одного агента;
- включить `stripe_connect`;
- включить real wallet enforcement;
- проверить:
  - onboarding
  - sale
  - reserve hold
  - refund calculate
  - refund execute
  - block
  - top-up
  - unblock
- подготовить rollback path.

### Exit criteria

- один агент проходит весь lifecycle;
- platform loss scenarios корректно закрываются.

## Phase 11. Broader Rollout

### Цель

Подготовить масштабирование на многих агентов.

### Deliverables

- reusable onboarding process;
- default templates;
- risk review checklist.

### Tasks

- шаблоны risk policy by country/currency;
- шаблоны credit limit by segment;
- автоматическое создание wallet/policy для нового агента;
- operational SOP для support team;
- training notes для super admin.

### Exit criteria

- новый агент может быть подключен без ручной импровизации;
- risk policy повторяема и масштабируема.

## Testing Backlog

### Unit tests

- formulas for risk capacity
- threshold transitions
- top-up allocation
- reserve hold calculation
- refund event counting
- payoutable calculation

### Integration tests

- sale posting creates correct ledger entries
- refund calculation produces expected breakdown
- refund execution updates wallet and status
- blocked agent cannot create checkout session
- payout denied for blocked agent
- top-up unblocks eligible agent

### Webhook tests

- checkout completed
- refund created
- payment failed
- dispute created
- account updated
- duplicate webhook idempotency

### Admin tests

- risk settings CRUD
- agent policy override CRUD
- wallet screen rendering
- ledger pagination/filtering
- refund preview flow

## Dependencies

- Stripe Connect onboarding and destination charges
- existing admin auth
- existing payments router
- Alembic migrations
- background jobs / scheduler
- structured logging

## Explicit Non-Goals for v1

- automated debt collection outside platform
- advanced dispute automation
- accounting export to ERP
- agent self-service legal workflow
- country-by-country legal decision engine

## Recommended Implementation Order

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6
8. Phase 7
9. Phase 8
10. Phase 9
11. Phase 10
12. Phase 11
