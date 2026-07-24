CREATE TABLE `password_recovery_tokens` (
  `id` text PRIMARY KEY NOT NULL,
  `user_id` text NOT NULL,
  `token_hash` text NOT NULL,
  `expires_at` text NOT NULL,
  `used_at` text,
  `created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE cascade
);--> statement-breakpoint
CREATE UNIQUE INDEX `password_recovery_hash_uq` ON `password_recovery_tokens` (`token_hash`);--> statement-breakpoint
CREATE INDEX `password_recovery_user_created_idx` ON `password_recovery_tokens` (`user_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `mfa_credentials` (
  `id` text PRIMARY KEY NOT NULL,
  `user_id` text NOT NULL,
  `secret_ciphertext` text NOT NULL,
  `recovery_codes_json` text DEFAULT '[]' NOT NULL,
  `enabled` integer DEFAULT false NOT NULL,
  `confirmed_at` text,
  `last_used_step` integer,
  `created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  `updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE cascade
);--> statement-breakpoint
CREATE UNIQUE INDEX `mfa_user_uq` ON `mfa_credentials` (`user_id`);
