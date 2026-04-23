# Stripe Connect Risk Architecture Specification

Дата: 2026-04-21
Статус: Draft v1
Область: TG-Ticket-Agent platform, Stripe Connect, agent risk accounting, refunds, monitoring

## 1. Цель

Построить платежную и риск-архитектуру для Stripe Connect, при которой:

- платформа удерживает свою комиссию с каждой продажи;
- агент получает деньги на свой connected account;
- любой refund, dispute, processing cost и операционный cost автоматически учитываются;
- платформа защищает себя от убытков через reserve, credit limit и autoblock;
- super admin управляет лимитами и политиками через админку;
- расчеты ведутся на уровне ledger, а не напрямую по таблице orders;
- Telegram checkout остается простым для пользователя, без e-mail confirmation flow.

## 2. Бизнес-принципы

### 2.1. Platform-first principle

Платформа не должна нести неучтенные убытки. Любая операция должна быть либо:

- оплачена пользователем;
- удержана с агента;
- покрыта reserve балансом агента;
- покрыта credit limit агента;
- вынесена в debt агента с автоматической блокировкой при достижении лимитов.

### 2.2. Every transaction is billable

Каждая транзакция и каждая операция обработки должна иметь финансовый след:

- покупка;
- сервисный сбор;
- комиссия платформы;
- Stripe processing cost;
- выдача билета;
- refund;
- возврат билета;
- dispute / chargeback;
- ручная корректировка;
- reserve hold / reserve release;
- payout.

### 2.3. Refund policy split

Система разделяет:

- customer-facing refund policy;
- agent liability policy.

Даже если customer refund по закону должен быть полным, экономические последствия могут быть переложены на агента по договору и через settlement logic платформы.

## 3. Целевая платежная модель

Используется:

- Stripe Connect;
- destination charges;
- Stripe-hosted onboarding;
- platform application fee;
- отдельный risk and settlement layer платформы.

Для агента поддерживается payment mode:

- `stripe_connect`

Старые потоки оплаты не считаются целевой схемой для Telegram UX и не используются как default для новой архитектуры.

## 4. Денежная модель заказа

Для каждого заказа должны храниться отдельные денежные компоненты.

### 4.1. Order amounts

- `ticket_amount_minor`
- `service_fee_amount_minor`
- `gross_amount_minor`
- `platform_fee_amount_minor`
- `stripe_fee_estimated_minor`
- `stripe_fee_actual_minor`
- `refund_total_minor`

Где:

- `gross_amount_minor = ticket_amount_minor + service_fee_amount_minor`
- `platform_fee_amount_minor` это платформа fee в рамках Connect / platform monetization
- `service_fee_amount_minor` это customer-facing fee, если он показывается отдельно

## 5. Risk buffer model

Вместо понятия "отрицательный депозит" используется модель:

- `reserve_balance`
- `credit_limit`
- `negative_exposure`
- `risk_capacity`

### 5.1. Definitions

- `reserve_balance_minor`: реальные удержанные средства агента
- `credit_limit_minor`: разрешенный минус за счет платформы
- `negative_exposure_minor`: уже реализованный риск / долг агента перед платформой
- `risk_capacity_minor`: оставшаяся емкость риска

### 5.2. Formula

`risk_capacity_minor = reserve_balance_minor + credit_limit_minor - negative_exposure_minor`

Если `risk_capacity_minor <= 0`, агент должен быть заблокирован автоматически, если не установлен manual override.

## 6. Статусы агента

### 6.1. Operational status

- `active`
- `warning`
- `restricted`
- `blocked`
- `force_blocked`

### 6.2. Meaning

- `active`: продажи и выплаты разрешены
- `warning`: продажи разрешены, выплаты могут быть ограничены, агент получает предупреждение
- `restricted`: продажи разрешены частично или выключены по policy, выплаты запрещены
- `blocked`: новые продажи и payout запрещены
- `force_blocked`: ручная блокировка super admin вне автоматической логики

## 7. Пороговая логика

Для защиты от случайной блокировки используются и денежные, и событийные пороги.

### 7.1. Money thresholds

- `warning_threshold_minor`
- `block_threshold_minor`

По умолчанию:

- `warning_threshold_minor = (reserve_balance_minor + credit_limit_minor) * warning_percent`
- `block_threshold_minor = reserve_balance_minor + credit_limit_minor`

### 7.2. Event thresholds

- `refund_event_warning_count`
- `refund_event_block_count`
- `refund_window_days`

### 7.3. Decision rules

Переход в `warning`, если:

- `negative_exposure_minor >= warning_threshold_minor`
- или `refund_count_in_window >= refund_event_warning_count`

Переход в `blocked`, если:

- `negative_exposure_minor >= block_threshold_minor`
- или `refund_count_in_window >= refund_event_block_count`
- или `manual_override_status = force_blocked`

## 8. Settlement source of truth

Источник истины для выплат и риска:

- `agent_ledger_entries`
- `agent_wallets`

Таблица `orders` не должна использоваться как прямой источник расчета payouts.

## 9. Таблицы БД

### 9.1. agent_wallets

- `id`
- `agent_id`
- `currency`
- `reserve_balance_minor`
- `credit_limit_minor`
- `negative_exposure_minor`
- `warning_threshold_minor`
- `block_threshold_minor`
- `status`
- `last_warning_at`
- `last_blocked_at`
- `updated_at`

### 9.2. agent_risk_policies

- `id`
- `agent_id`
- `allow_negative_balance`
- `auto_block_enabled`
- `refund_window_days`
- `refund_event_warning_count`
- `refund_event_block_count`
- `rolling_reserve_percent_bps`
- `min_reserve_balance_minor`
- `manual_override_status`
- `created_at`
- `updated_at`

### 9.3. agent_ledger_entries

- `id`
- `agent_id`
- `wallet_id`
- `order_id`
- `refund_case_id`
- `currency`
- `amount_minor`
- `direction`
- `entry_type`
- `source`
- `source_id`
- `description`
- `metadata_json`
- `created_at`

### 9.4. refund_cases

- `id`
- `order_id`
- `agent_id`
- `currency`
- `customer_refund_amount_minor`
- `ticket_refund_amount_minor`
- `service_fee_refund_amount_minor`
- `platform_cost_amount_minor`
- `agent_debit_amount_minor`
- `stripe_refund_id`
- `status`
- `policy_applied`
- `reason`
- `created_at`
- `completed_at`

### 9.5. platform_risk_settings

Либо отдельная таблица, либо системные settings key/value.

Должны храниться:

- default credit limits by currency
- default warning thresholds
- default block thresholds
- refund event thresholds
- rolling reserve defaults
- safety buffer defaults
- auto-block defaults

## 10. Расширения существующих таблиц

### 10.1. agents

Добавить:

- `payment_type`
- `stripe_account_id`
- `stripe_account_status`
- `stripe_charges_enabled`
- `stripe_payouts_enabled`
- `agent_operational_status`

### 10.2. orders

Добавить:

- `ticket_amount_minor`
- `service_fee_amount_minor`
- `gross_amount_minor`
- `platform_fee_amount_minor`
- `stripe_fee_estimated_minor`
- `stripe_fee_actual_minor`
- `payment_provider`
- `stripe_session_id`
- `stripe_payment_intent_id`
- `stripe_charge_id`
- `stripe_transfer_id`
- `stripe_application_fee_amount_minor`
- `refund_total_minor`
- `risk_state`

## 11. Enum values

### 11.1. wallet.status

- `active`
- `warning`
- `restricted`
- `blocked`

### 11.2. ledger.direction

- `credit`
- `debit`

### 11.3. ledger.entry_type

- `sale_credit`
- `platform_fee_credit`
- `processing_fee_debit`
- `reserve_hold`
- `reserve_release`
- `refund_debit`
- `refund_processing_cost_debit`
- `dispute_debit`
- `manual_adjustment`
- `topup_credit`
- `payout_debit`

### 11.4. refund_cases.status

- `pending`
- `calculated`
- `submitted`
- `completed`
- `failed`
- `manual_review`

## 12. Lifecycle: sale flow

### 12.1. Sale completion

На `checkout.session.completed`:

1. пометить order как paid;
2. сохранить Stripe IDs;
3. записать ledger:
   - `sale_credit`
   - `platform_fee_credit`
   - `processing_fee_debit` по policy
   - `reserve_hold`, если включен rolling reserve;
4. пересчитать wallet;
5. пересчитать agent status;
6. запустить ticket delivery.

### 12.2. Reserve hold

Если включен rolling reserve:

`reserve_hold_minor = gross_or_ticket_base * rolling_reserve_percent_bps / 10000`

Конкретная база расчета должна быть настраиваемой:

- по `ticket_amount_minor`
- или по `gross_amount_minor`

## 13. Lifecycle: refund flow

### 13.1. Refund pre-calculation

Перед выполнением refund система обязана посчитать:

- `customer_refund_amount_minor`
- `ticket_refund_amount_minor`
- `service_fee_refund_amount_minor`
- `platform_cost_amount_minor`
- `agent_debit_amount_minor`
- `post_refund_negative_exposure_minor`
- `post_refund_agent_status`

### 13.2. Refund execution

После успешного refund в Stripe:

1. создать или обновить `refund_case`;
2. записать ledger:
   - `refund_debit`
   - `refund_processing_cost_debit`
   - `reserve_release` или reserve consumption;
3. обновить `negative_exposure_minor`;
4. пересчитать wallet/status;
5. если достигнут hard threshold, перевести агента в `blocked`;
6. отправить уведомления платформе и агенту.

## 14. Что входит в negative exposure

В `negative_exposure_minor` должны попадать:

- amount, профинансированный платформой при refund;
- Stripe refund cost;
- non-recoverable processing fees;
- dispute / chargeback losses;
- unrecovered service fee, если platform обязана вернуть ее пользователю;
- ticket cancellation / ticket return operational cost;
- ручные дебетовые корректировки.

## 15. Refund policy engine

Система должна поддерживать минимум три refund mode:

- `full_refund`
- `ticket_only_refund`
- `custom_partial_refund`

При этом engine не выполняет refund без предварительного расчета.

Каждый refund должен получать:

- `policy_applied`
- `reason`
- `liability_split`

## 16. Payout logic

Формула:

`payoutable_minor = credits - debits - holds`

Payout возможен только если:

- `agent_operational_status = active`
- `negative_exposure_minor < block_threshold_minor`
- `manual_override_status != force_blocked`
- reserve balance не нарушает policy

Если агент в `warning`, payout policy должна быть настраиваемой:

- payout allowed
- payout held
- partial payout

Для v1 рекомендуется:

- при `warning`: выплаты hold
- при `blocked`: выплаты запрещены

## 17. Top-up logic

При топ-апе агента:

1. сумма сначала гасит `negative_exposure_minor`;
2. остаток переводится в `reserve_balance_minor`;
3. затем пересчитываются thresholds и status.

Формула:

`top_up_required_minor = max(0, negative_exposure_minor - reserve_balance_minor - credit_limit_minor + safety_buffer_minor)`

## 18. Monitoring and continuous control

### 18.1. Synchronous checks

Проверка должна выполняться на:

- sale completed
- refund calculated
- refund executed
- dispute created
- payout requested
- top-up processed
- manual adjustment

### 18.2. Asynchronous jobs

Нужны background jobs:

- hourly wallet reconciliation
- daily ledger integrity check
- daily blocked-agent report
- stale negative balance monitor
- unmatched Stripe event monitor

### 18.3. Alerts

События:

- `agent_warning_threshold_reached`
- `agent_blocked_negative_exposure`
- `agent_refund_event_limit_reached`
- `refund_without_reverse_transfer`
- `ledger_imbalance_detected`
- `payout_attempt_blocked_agent`
- `negative_balance_persisting`

## 19. Super admin configurability

Super admin должен настраивать:

### 19.1. Global by currency

- `default_credit_limit_minor`
- `default_warning_percent`
- `default_block_threshold_strategy`
- `default_safety_buffer_minor`
- `default_min_reserve_balance_minor`

### 19.2. Global event logic

- `refund_window_days`
- `refund_event_warning_count`
- `refund_event_block_count`
- `auto_block_enabled`

### 19.3. Global reserve logic

- `rolling_reserve_percent_bps`
- `reserve_release_days`
- `reserve_base_amount_mode`

### 19.4. Per-agent overrides

- `credit_limit_minor`
- `warning_threshold_minor`
- `block_threshold_minor`
- `refund_event_warning_count`
- `refund_event_block_count`
- `rolling_reserve_percent_bps`
- `manual_override_status`

## 20. Admin UI requirements

### 20.1. Super admin risk settings screen

Должна отображать:

- defaults by currency
- thresholds
- reserve logic
- block policy
- safety buffers
- enable/disable auto-block

### 20.2. Agent risk profile screen

Должна отображать:

- reserve balance
- credit limit
- current negative exposure
- remaining risk capacity
- current status
- top-up required
- refund incidents
- dispute incidents
- wallet history
- ledger history

## 21. Hard platform guarantees

Для v1 система должна гарантировать:

- ни один refund не выполняется без pre-calculation;
- ни один payout не выполняется без wallet/status check;
- заблокированный агент не может создавать новые checkout sessions;
- все денежные изменения отражаются в ledger;
- любой drift между Stripe и ledger поднимает alert.

## 22. Rollout strategy

1. Сначала вводится schema и ledger.
2. Затем расчеты работают в shadow mode без блокировок.
3. Затем включается warning mode.
4. Затем restriction mode.
5. Затем hard block.
6. После этого activation на одном тестовом агенте.

## 23. Non-goals for v1

Не входят в первую версию:

- полная dispute automation;
- self-service payouts dashboard для агента;
- автоматическое взыскание долга с банковского счета агента;
- продвинутый legal engine по юрисдикциям;
- multi-entity tax accounting.

## 24. Critical note

Договор с агентом обязателен, но сам по себе не защищает платформу от кассового риска. Реальная защита достигается только комбинацией:

- ledger accounting;
- reserve balance;
- configurable credit limit;
- monitoring;
- automatic enforcement.
