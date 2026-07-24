CREATE TABLE `tiktok_oauth_states` (
	`id` text PRIMARY KEY NOT NULL,
	`state_hash` text NOT NULL,
	`organization_id` text NOT NULL,
	`user_id` text NOT NULL,
	`redirect_after` text DEFAULT '/' NOT NULL,
	`expires_at` text NOT NULL,
	`consumed_at` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `tiktok_oauth_states_state_hash_unique` ON `tiktok_oauth_states` (`state_hash`);--> statement-breakpoint
CREATE TABLE `tiktok_connections` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`connected_by` text NOT NULL,
	`open_id` text NOT NULL,
	`display_name` text,
	`avatar_url` text,
	`access_token_ciphertext` text NOT NULL,
	`refresh_token_ciphertext` text NOT NULL,
	`scopes_json` text DEFAULT '[]' NOT NULL,
	`access_expires_at` text NOT NULL,
	`refresh_expires_at` text NOT NULL,
	`status` text DEFAULT 'active' NOT NULL,
	`is_mock` integer DEFAULT false NOT NULL,
	`creator_info_json` text,
	`creator_info_fetched_at` text,
	`last_error_code` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`connected_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `tiktok_org_open_id_uq` ON `tiktok_connections` (`organization_id`,`open_id`);--> statement-breakpoint
CREATE TABLE `publication_jobs` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`video_project_id` text NOT NULL,
	`scheduled_slot_id` text NOT NULL,
	`connection_id` text NOT NULL,
	`requested_by` text NOT NULL,
	`output_asset_id` text NOT NULL,
	`idempotency_key` text NOT NULL,
	`payload_hash` text NOT NULL,
	`publish_mode` text DEFAULT 'direct_post' NOT NULL,
	`caption` text DEFAULT '' NOT NULL,
	`privacy_level` text,
	`disable_comment` integer DEFAULT true NOT NULL,
	`disable_duet` integer DEFAULT true NOT NULL,
	`disable_stitch` integer DEFAULT true NOT NULL,
	`brand_content_toggle` integer DEFAULT false NOT NULL,
	`brand_organic_toggle` integer DEFAULT false NOT NULL,
	`is_aigc` integer DEFAULT false NOT NULL,
	`consented_at` text NOT NULL,
	`scheduled_for` text NOT NULL,
	`status` text DEFAULT 'queued' NOT NULL,
	`publish_id` text,
	`post_id` text,
	`attempts` integer DEFAULT 0 NOT NULL,
	`provider_log_id` text,
	`error_code` text,
	`error_message` text,
	`is_mock` integer DEFAULT false NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`video_project_id`) REFERENCES `video_projects`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`scheduled_slot_id`) REFERENCES `scheduled_slots`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`connection_id`) REFERENCES `tiktok_connections`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`requested_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`output_asset_id`) REFERENCES `media_assets`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `publication_jobs_idempotency_key_unique` ON `publication_jobs` (`idempotency_key`);--> statement-breakpoint
CREATE TABLE `publication_events` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`publication_job_id` text NOT NULL,
	`event_type` text NOT NULL,
	`payload_json` text DEFAULT '{}' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`publication_job_id`) REFERENCES `publication_jobs`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE TABLE `tiktok_webhook_receipts` (
	`id` text PRIMARY KEY NOT NULL,
	`delivery_hash` text NOT NULL,
	`event_type` text NOT NULL,
	`open_id` text,
	`payload_json` text NOT NULL,
	`processed` integer DEFAULT false NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);--> statement-breakpoint
CREATE UNIQUE INDEX `tiktok_webhook_receipts_delivery_hash_unique` ON `tiktok_webhook_receipts` (`delivery_hash`);
