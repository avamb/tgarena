# Implementation-Ready Plan: Stripe Connect Risk Accounting

Дата: 2026-04-21
Статус: Ready for implementation planning
Основано на:

- `Specifications/stripe-connect-risk-architecture.md`
- `Specifications/implementation-backlog.md`

## 1. Цель документа

Этот документ переводит архитектуру в набор конкретных задач для реализации:

- какие файлы и модули затрагиваются;
- какие таблицы и миграции нужны;
- какие API endpoints добавляются;
- какие enum и DTO вводятся;
- какие тесты обязательны;
- в каком порядке это безопасно внедрять.

Документ рассчитан на поэтапную разработку без поломки текущего bot-flow.

## 2. Жесткие ограничения реализации

### 2.1. Не ломать текущий bot purchase flow

До включения `stripe_connect` на агенте:

- существующий bot flow должен работать как сейчас;
- `bill24_acquiring` и текущая логика заказов должны оставаться совместимыми;
- новые поля БД должны быть backward-compatible;
- новые проверки риска не должны блокировать текущие продажи в shadow mode.

### 2.2. Source of truth

После внедрения risk accounting:

- `orders` остаются бизнес-объектами;
- `agent_ledger_entries` и `agent_wallets` становятся settlement source of truth;
- payouts и risk decisions не должны считаться напрямую из `orders`.

### 2.3. Rollout rule

Сначала:

- schema;
- ledger;
- shadow mode;
- warning mode;

Потом:

- real enforcement;
- только один агент.

## 3. Целевой модульный дизайн

## 3.1. Backend modules

Новые модули:

- `backend/app/services/stripe_connect.py`
- `backend/app/services/ledger.py`
- `backend/app/services/wallets.py`
- `backend/app/services/risk_engine.py`
- `backend/app/services/refunds.py`

Возможные дополнительные helper modules:

- `backend/app/services/money.py`
- `backend/app/services/payouts.py`

## 3.2. Existing files to extend

- [backend/app/models/__init__.py](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/backend/app/models/__init__.py)
- [backend/app/api/payments.py](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/backend/app/api/payments.py)
- [backend/app/api/admin.py](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/backend/app/api/admin.py)
- [backend/app/core/config.py](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/backend/app/core/config.py)
- [backend/app/main.py](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/backend/app/main.py)
- [admin/src/pages/Agents.tsx](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/admin/src/pages/Agents.tsx)
- [admin/src/pages/AgentDetails.tsx](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/admin/src/pages/AgentDetails.tsx)
- [admin/src/pages/Settings.tsx](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/admin/src/pages/Settings.tsx)

## 4. Phase 1: Database schema

## 4.1. Migration name

Рекомендуемое имя миграции:

- `20260421_000001_add_agent_risk_accounting.py`

Если Connect onboarding входит в тот же этап:

- `20260421_000002_add_stripe_connect_fields.py`

## 4.2. New tables

### `agent_wallets`

Поля:

- `id` PK
- `agent_id` FK -> `agents.id`
- `currency` VARCHAR(3) NOT NULL
- `reserve_balance_minor` BIGINT NOT NULL DEFAULT 0
- `credit_limit_minor` BIGINT NOT NULL DEFAULT 0
- `negative_exposure_minor` BIGINT NOT NULL DEFAULT 0
- `warning_threshold_minor` BIGINT NOT NULL DEFAULT 0
- `block_threshold_minor` BIGINT NOT NULL DEFAULT 0
- `status` VARCHAR(20) NOT NULL DEFAULT `active`
- `last_warning_at` TIMESTAMP NULL
- `last_blocked_at` TIMESTAMP NULL
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

Indexes:

- `(agent_id, currency)` unique
- `(status)`

### `agent_risk_policies`

Поля:

- `id` PK
- `agent_id` FK -> `agents.id`
- `allow_negative_balance` BOOLEAN NOT NULL DEFAULT TRUE
- `auto_block_enabled` BOOLEAN NOT NULL DEFAULT TRUE
- `refund_window_days` INTEGER NOT NULL DEFAULT 30
- `refund_event_warning_count` INTEGER NOT NULL DEFAULT 3
- `refund_event_block_count` INTEGER NOT NULL DEFAULT 7
- `rolling_reserve_percent_bps` INTEGER NOT NULL DEFAULT 0
- `min_reserve_balance_minor` BIGINT NOT NULL DEFAULT 0
- `manual_override_status` VARCHAR(20) NULL
- `created_at` TIMESTAMP NOT NULL
- `updated_at` TIMESTAMP NOT NULL

Indexes:

- `(agent_id)` unique

### `agent_ledger_entries`

Поля:

- `id` PK
- `agent_id` FK -> `agents.id`
- `wallet_id` FK -> `agent_wallets.id`
- `order_id` FK -> `orders.id` NULL
- `refund_case_id` FK -> `refund_cases.id` NULL
- `currency` VARCHAR(3) NOT NULL
- `amount_minor` BIGINT NOT NULL
- `direction` VARCHAR(10) NOT NULL
- `entry_type` VARCHAR(50) NOT NULL
- `source` VARCHAR(50) NOT NULL
- `source_id` VARCHAR(255) NULL
- `description` TEXT NULL
- `metadata_json` JSONB NOT NULL DEFAULT `'{}'`
- `created_at` TIMESTAMP NOT NULL

Indexes:

- `(agent_id, currency, created_at)`
- `(order_id)`
- `(refund_case_id)`
- `(entry_type)`

### `refund_cases`

Поля:

- `id` PK
- `order_id` FK -> `orders.id`
- `agent_id` FK -> `agents.id`
- `currency` VARCHAR(3) NOT NULL
- `customer_refund_amount_minor` BIGINT NOT NULL DEFAULT 0
- `ticket_refund_amount_minor` BIGINT NOT NULL DEFAULT 0
- `service_fee_refund_amount_minor` BIGINT NOT NULL DEFAULT 0
- `platform_cost_amount_minor` BIGINT NOT NULL DEFAULT 0
- `agent_debit_amount_minor` BIGINT NOT NULL DEFAULT 0
- `stripe_refund_id` VARCHAR(255) NULL
- `status` VARCHAR(20) NOT NULL DEFAULT `pending`
- `policy_applied` VARCHAR(50) NULL
- `reason` TEXT NULL
- `created_at` TIMESTAMP NOT NULL
- `completed_at` TIMESTAMP NULL

Indexes:

- `(order_id)`
- `(agent_id, created_at)`
- `(status)`

## 4.3. Existing table changes

### `agents`

Добавить:

- `payment_type` VARCHAR(30) NOT NULL DEFAULT `bill24_acquiring`
- `stripe_account_id` VARCHAR(255) NULL
- `stripe_account_status` VARCHAR(50) NULL
- `stripe_charges_enabled` BOOLEAN NOT NULL DEFAULT FALSE
- `stripe_payouts_enabled` BOOLEAN NOT NULL DEFAULT FALSE
- `agent_operational_status` VARCHAR(20) NOT NULL DEFAULT `active`

### `orders`

Добавить:

- `ticket_amount_minor` BIGINT NULL
- `service_fee_amount_minor` BIGINT NULL
- `gross_amount_minor` BIGINT NULL
- `platform_fee_amount_minor` BIGINT NULL
- `stripe_fee_estimated_minor` BIGINT NULL
- `stripe_fee_actual_minor` BIGINT NULL
- `payment_provider` VARCHAR(30) NULL
- `stripe_session_id` VARCHAR(255) NULL
- `stripe_payment_intent_id` VARCHAR(255) NULL
- `stripe_charge_id` VARCHAR(255) NULL
- `stripe_transfer_id` VARCHAR(255) NULL
- `stripe_application_fee_amount_minor` BIGINT NULL
- `refund_total_minor` BIGINT NOT NULL DEFAULT 0
- `risk_state` VARCHAR(30) NULL

## 4.4. Model implementation file

Основная модельная работа:

- [backend/app/models/__init__.py](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/backend/app/models/__init__.py)

Рекомендация:

- добавить новые SQLAlchemy models в тот же файл для v1;
- при росте модуля позже можно вынести в отдельные model files.

## 5. Phase 2: Domain enums and money conventions

## 5.1. Money convention

Все новые settlement суммы хранить в `minor units`.

Примеры:

- EUR 1.00 -> `100`
- USD 1.00 -> `100`
- ILS 10.50 -> `1050`

Текущий `orders.total_sum` остается для backward compatibility, но новые расчеты должны опираться на `*_minor`.

## 5.2. Enum definitions

Рекомендуемые Python enums:

- `WalletStatus`
- `LedgerDirection`
- `LedgerEntryType`
- `RefundCaseStatus`
- `AgentOperationalStatus`

Рекомендуемое место:

- `backend/app/models/enums.py`

Если не хочется распиливать модели на v1:

- можно временно хранить enums в `models/__init__.py`

## 5.3. Money helpers

Создать:

- `backend/app/services/money.py`

Функции:

- `to_minor(amount: Decimal | float, currency: str) -> int`
- `from_minor(amount_minor: int, currency: str) -> Decimal`
- `normalize_currency(code: str) -> str`

## 6. Phase 3: Ledger service

## 6.1. New file

- `backend/app/services/ledger.py`

## 6.2. Required methods

- `post_entry(...)`
- `post_entries(...)`
- `get_wallet_for_agent_currency(agent_id, currency)`
- `ensure_wallet_exists(agent_id, currency, db)`
- `rebuild_wallet_from_ledger(wallet_id, db)`

## 6.3. Posting interface

Минимальный интерфейс для posting:

- `agent_id`
- `currency`
- `amount_minor`
- `direction`
- `entry_type`
- `order_id`
- `refund_case_id`
- `source`
- `source_id`
- `description`
- `metadata`

## 6.4. Idempotency requirement

Для webhook и повторных processing вызовов `post_entries` должен поддерживать idempotency через:

- `source`
- `source_id`
- `entry_type`

## 7. Phase 4: Wallet service

## 7.1. New file

- `backend/app/services/wallets.py`

## 7.2. Required methods

- `recompute_wallet(wallet_id, db)`
- `recompute_agent_wallets(agent_id, db)`
- `calculate_risk_capacity(wallet)`
- `calculate_top_up_required(wallet, safety_buffer_minor)`
- `apply_top_up(agent_id, currency, amount_minor, db)`

## 7.3. Wallet recompute formula

Использовать агрегирование ledger:

- `credits_total`
- `debits_total`
- `reserve_balance_minor`
- `negative_exposure_minor`

Рекомендация:

- reserve and exposure должны выводиться не из manual fields alone, а из entry types
- denormalized поля в `agent_wallets` обновляются функцией recompute

## 8. Phase 5: Risk engine

## 8.1. New file

- `backend/app/services/risk_engine.py`

## 8.2. Required methods

- `evaluate_wallet_status(wallet, policy, refund_event_count)`
- `count_refund_events(agent_id, window_days, db)`
- `should_block_agent(...)`
- `should_warn_agent(...)`
- `apply_agent_status(agent, wallet, status, db)`

## 8.3. Decision output DTO

Рекомендуемый internal DTO:

- `status_before`
- `status_after`
- `warning_triggered`
- `block_triggered`
- `money_threshold_hit`
- `event_threshold_hit`
- `remaining_risk_capacity_minor`
- `top_up_required_minor`

## 8.4. Enforcement points

Risk engine должен вызываться:

- после sale posting
- после refund posting
- после top-up
- после manual adjustment
- перед payout

## 9. Phase 6: Stripe Connect service

## 9.1. New file

- `backend/app/services/stripe_connect.py`

## 9.2. Required methods

- `create_connected_account(agent, db)`
- `create_onboarding_link(agent, refresh_url, return_url)`
- `refresh_account_status(agent, db)`
- `build_destination_charge_payload(order, agent, fee_minor)`
- `verify_webhook_signature(payload, sig_header)`

## 9.3. Config additions

В [backend/app/core/config.py](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/backend/app/core/config.py) добавить:

- `STRIPE_CONNECT_RETURN_URL`
- `STRIPE_CONNECT_REFRESH_URL`

При необходимости:

- `STRIPE_CONNECT_PLATFORM_COUNTRY`

## 10. Phase 7: Payments API changes

## 10.1. File

- [backend/app/api/payments.py](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/backend/app/api/payments.py)

## 10.2. Existing endpoint to extend

- `POST /api/payments/create-session`

## 10.3. New create-session behavior

Если `agent.payment_type == stripe_connect`:

- проверить `stripe_account_id`
- проверить `stripe_charges_enabled`
- вычислить `platform_fee_amount_minor`
- создать Checkout Session для destination charge
- сохранить Stripe IDs и amount breakdown в `orders`

Если агент не готов:

- вернуть controlled 400/409 ошибку

## 10.4. New webhook endpoint

Добавить:

- `POST /api/payments/stripe/webhook`

Обрабатывать:

- `checkout.session.completed`
- `payment_intent.payment_failed`
- `charge.refunded`
- `charge.dispute.created`
- `account.updated`

## 10.5. Webhook pipeline

На `checkout.session.completed`:

- найти order
- сохранить Stripe IDs
- выполнить ledger postings sale phase
- recompute wallet
- run risk engine
- если order еще не paid, выставить paid
- запустить ticket delivery

## 11. Phase 8: Refund service

## 11.1. New file

- `backend/app/services/refunds.py`

## 11.2. Required methods

- `calculate_refund(order, mode, reason, db)`
- `execute_refund(refund_case_id, db)`
- `build_agent_debit_entries(refund_case, db)`
- `apply_refund_outcome(refund_case, db)`

## 11.3. Refund modes

- `full_refund`
- `ticket_only_refund`
- `custom_partial_refund`

## 11.4. Calculation output

Возвращать:

- `customer_refund_amount_minor`
- `ticket_refund_amount_minor`
- `service_fee_refund_amount_minor`
- `platform_cost_amount_minor`
- `agent_debit_amount_minor`
- `post_refund_status`
- `top_up_required_minor`

## 12. Phase 9: Admin API changes

## 12.1. File

- [backend/app/api/admin.py](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/backend/app/api/admin.py)

## 12.2. New agent endpoints

- `GET /api/admin/agents/{id}/wallets`
- `GET /api/admin/agents/{id}/risk-policy`
- `PUT /api/admin/agents/{id}/risk-policy`
- `GET /api/admin/agents/{id}/ledger`
- `GET /api/admin/agents/{id}/risk-incidents`
- `POST /api/admin/agents/{id}/topup`
- `POST /api/admin/agents/{id}/block`
- `POST /api/admin/agents/{id}/unblock`

## 12.3. New Stripe admin endpoints

- `POST /api/admin/agents/{id}/stripe/account`
- `POST /api/admin/agents/{id}/stripe/onboarding-link`
- `GET /api/admin/agents/{id}/stripe/status`

## 12.4. New refund admin endpoints

- `POST /api/admin/orders/{id}/refund/calculate`
- `POST /api/admin/orders/{id}/refund/execute`

## 12.5. New risk settings endpoints

- `GET /api/admin/risk/settings`
- `PUT /api/admin/risk/settings`

## 13. Phase 10: Admin UI tasks

## 13.1. Settings page

Файл:

- [admin/src/pages/Settings.tsx](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/admin/src/pages/Settings.tsx)

Что изменить:

- убрать хранение risk/payment settings только в `localStorage`
- перевести на backend API
- добавить блоки:
  - global credit limits
  - refund thresholds
  - reserve settings
  - auto-block toggle

## 13.2. Agents list page

Файл:

- [admin/src/pages/Agents.tsx](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/admin/src/pages/Agents.tsx)

Что добавить:

- индикатор operational status
- индикатор Stripe account readiness
- быстрые action buttons:
  - create account
  - continue onboarding
  - open wallet view

## 13.3. Agent details page

Файл:

- [admin/src/pages/AgentDetails.tsx](/C:/Projects/TG_Ticket_Agent/TG-Ticket-Agent/admin/src/pages/AgentDetails.tsx)

Что добавить:

- wallet summary
- reserve balance
- credit limit
- negative exposure
- remaining capacity
- top-up required
- risk policy editor
- ledger table
- incidents table

## 13.4. New pages recommended

- `admin/src/pages/RiskSettings.tsx`
- `admin/src/pages/AgentLedger.tsx` or embedded section
- `admin/src/pages/RiskIncidents.tsx`

## 14. Phase 11: Background jobs

## 14.1. Candidate file

- `backend/app/core/background_jobs.py`

## 14.2. Jobs to add

- `reconcile_wallets_job`
- `verify_ledger_integrity_job`
- `blocked_agents_report_job`
- `negative_balance_watchdog_job`

## 14.3. Scheduling

Если scheduler already exists, использовать его. Иначе:

- hourly jobs
- daily summary jobs

## 15. Phase 12: Observability

## 15.1. Logging

Каждая финансовая операция должна логировать:

- `agent_id`
- `order_id`
- `currency`
- `entry_type`
- `amount_minor`
- `wallet_status_before`
- `wallet_status_after`
- `remaining_risk_capacity_minor`

## 15.2. Alert categories

- `warning_threshold_reached`
- `block_threshold_reached`
- `refund_limit_reached`
- `webhook_signature_failed`
- `stripe_reconciliation_mismatch`
- `payout_blocked`

## 16. Phase 13: Shadow mode

## 16.1. Feature flag

Нужен feature flag:

- `RISK_ENGINE_MODE = shadow | warning | enforce`

Рекомендуемое место:

- env setting initially
- позже можно вынести в admin settings

## 16.2. Behavior by mode

`shadow`

- считаем balances и статусы
- ничего не блокируем

`warning`

- считаем balances
- отправляем предупреждения
- payouts hold optional

`enforce`

- реально блокируем checkout/payout

## 17. Tests: required inventory

## 17.1. New test files recommended

- `backend/tests/test_wallet_service.py`
- `backend/tests/test_ledger_service.py`
- `backend/tests/test_risk_engine.py`
- `backend/tests/test_refund_calculation.py`
- `backend/tests/test_refund_execution.py`
- `backend/tests/test_stripe_connect_checkout.py`
- `backend/tests/test_stripe_webhook_processing.py`
- `backend/tests/test_agent_blocking.py`

## 17.2. Must-have unit tests

- money to minor conversion
- risk capacity formula
- warning/block threshold transitions
- top-up allocation
- refund event counting
- payoutable formula

## 17.3. Must-have integration tests

- sale posting creates expected ledger entries
- wallet recompute matches expected balances
- refund calculate returns correct breakdown
- refund execute updates wallet and order
- blocked agent cannot create new checkout session
- top-up unblocks agent when conditions met

## 17.4. Webhook tests

- duplicate webhook idempotency
- sale completion webhook
- refund webhook
- dispute webhook
- account updated webhook

## 18. Acceptance criteria by implementation phase

## 18.1. Schema phase accepted when

- migrations apply cleanly
- old orders and agents still read correctly
- new tables present and indexed

## 18.2. Ledger phase accepted when

- wallet can be rebuilt from ledger only
- duplicate posting is prevented

## 18.3. Payments phase accepted when

- one agent can onboard into Stripe Connect
- checkout session uses destination charges
- webhook can mark order paid

## 18.4. Refund phase accepted when

- every refund has a `refund_case`
- every refund changes ledger and wallet
- negative exposure is updated deterministically

## 18.5. Enforcement phase accepted when

- blocked agent cannot sell
- blocked agent cannot receive payout
- top-up can recover agent state

## 19. Suggested implementation order for the first coding sprint

Sprint 1:

- Phase 1 schema
- Phase 2 money/enums
- Phase 3 ledger service
- Phase 4 wallet recompute

Sprint 2:

- Stripe Connect account onboarding
- create-session extension
- webhook skeleton

Sprint 3:

- sale postings
- risk engine
- shadow mode

Sprint 4:

- refund calculation
- refund execution
- negative exposure logic

Sprint 5:

- admin UI
- top-up and block/unblock
- monitoring jobs

## 20. Explicit implementation note

В первой реализации не стоит пытаться одновременно сделать:

- full payout subsystem;
- country-specific legal rules engine;
- dispute automation;
- agent self-service debt repayment.

Правильный v1 фокус:

- deterministic accounting
- risk visibility
- controlled blocking
- one-agent rollout
