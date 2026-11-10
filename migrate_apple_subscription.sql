BEGIN;

ALTER TABLE app_subscriptions
ADD COLUMN IF NOT EXISTS original_transaction_id VARCHAR(128);

CREATE UNIQUE INDEX IF NOT EXISTS
ix_app_subscriptions_original_transaction_id
ON app_subscriptions (original_transaction_id);

COMMIT;
