CREATE TABLE `operational_errors` (
  `id` text PRIMARY KEY NOT NULL,
  `organization_id` text,
  `service` text NOT NULL,
  `code` text NOT NULL,
  `severity` text DEFAULT 'error' NOT NULL,
  `status` text DEFAULT 'open' NOT NULL,
  `message_sanitized` text NOT NULL,
  `fingerprint` text NOT NULL,
  `request_id` text,
  `occurrences` integer DEFAULT 1 NOT NULL,
  `corrective_action` text,
  `resolved_by` text,
  `first_seen_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  `last_seen_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  `resolved_at` text,
  FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON DELETE cascade,
  FOREIGN KEY (`resolved_by`) REFERENCES `users`(`id`) ON DELETE set null
);--> statement-breakpoint
CREATE INDEX `operational_error_status_seen_idx` ON `operational_errors` (`status`,`last_seen_at`);--> statement-breakpoint
CREATE INDEX `operational_error_org_status_idx` ON `operational_errors` (`organization_id`,`status`);--> statement-breakpoint
CREATE TABLE `cost_budgets` (
  `id` text PRIMARY KEY NOT NULL,
  `organization_id` text NOT NULL,
  `monthly_limit_cents` integer NOT NULL,
  `warning_percent` integer DEFAULT 80 NOT NULL,
  `hard_stop_enabled` integer DEFAULT false NOT NULL,
  `currency` text DEFAULT 'BRL' NOT NULL,
  `updated_by` text NOT NULL,
  `created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  `updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON DELETE cascade,
  FOREIGN KEY (`updated_by`) REFERENCES `users`(`id`)
);--> statement-breakpoint
CREATE UNIQUE INDEX `cost_budget_org_uq` ON `cost_budgets` (`organization_id`);--> statement-breakpoint
CREATE TABLE `cost_ledger_entries` (
  `id` text PRIMARY KEY NOT NULL,
  `organization_id` text NOT NULL,
  `provider` text NOT NULL,
  `category` text NOT NULL,
  `amount_micros` integer NOT NULL,
  `quantity` integer DEFAULT 1 NOT NULL,
  `unit` text DEFAULT 'operation' NOT NULL,
  `source_ref` text NOT NULL,
  `is_mock` integer DEFAULT false NOT NULL,
  `occurred_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON DELETE cascade
);--> statement-breakpoint
CREATE UNIQUE INDEX `cost_org_source_uq` ON `cost_ledger_entries` (`organization_id`,`source_ref`);--> statement-breakpoint
CREATE INDEX `cost_org_occurred_idx` ON `cost_ledger_entries` (`organization_id`,`occurred_at`);--> statement-breakpoint
CREATE TABLE `backup_runs` (
  `id` text PRIMARY KEY NOT NULL,
  `environment` text NOT NULL,
  `kind` text NOT NULL,
  `status` text NOT NULL,
  `storage_key` text,
  `checksum_sha256` text,
  `size_bytes` integer,
  `started_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  `completed_at` text,
  `error_code` text
);--> statement-breakpoint
CREATE INDEX `backup_environment_started_idx` ON `backup_runs` (`environment`,`started_at`);--> statement-breakpoint
CREATE TABLE `audit_checkpoints` (
  `id` text PRIMARY KEY NOT NULL,
  `organization_id` text NOT NULL,
  `created_by` text NOT NULL,
  `from_at` text NOT NULL,
  `to_at` text NOT NULL,
  `entry_count` integer NOT NULL,
  `digest_sha256` text NOT NULL,
  `created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON DELETE cascade,
  FOREIGN KEY (`created_by`) REFERENCES `users`(`id`)
);--> statement-breakpoint
CREATE INDEX `audit_checkpoint_org_created_idx` ON `audit_checkpoints` (`organization_id`,`created_at`);
