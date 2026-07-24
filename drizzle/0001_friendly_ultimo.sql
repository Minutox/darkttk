CREATE TABLE `ai_providers` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`capability` text NOT NULL,
	`provider_key` text NOT NULL,
	`display_name` text NOT NULL,
	`enabled` integer DEFAULT false NOT NULL,
	`is_mock` integer DEFAULT true NOT NULL,
	`config_json` text DEFAULT '{}' NOT NULL,
	`secret_ref` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `provider_org_capability_key_uq` ON `ai_providers` (`organization_id`,`capability`,`provider_key`);--> statement-breakpoint
CREATE TABLE `content_events` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`actor_id` text,
	`subject_type` text NOT NULL,
	`subject_id` text NOT NULL,
	`event_type` text NOT NULL,
	`payload_json` text DEFAULT '{}' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`actor_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `fact_checks` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`script_id` text NOT NULL,
	`source_id` text,
	`claim` text NOT NULL,
	`verdict` text NOT NULL,
	`confidence` integer DEFAULT 0 NOT NULL,
	`evidence` text NOT NULL,
	`provider_key` text NOT NULL,
	`reviewed_by` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`script_id`) REFERENCES `scripts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`source_id`) REFERENCES `sources`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`reviewed_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `moderation_checks` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`subject_type` text NOT NULL,
	`subject_id` text NOT NULL,
	`stage` text NOT NULL,
	`result` text NOT NULL,
	`matched_rules_json` text DEFAULT '[]' NOT NULL,
	`policy_version` text NOT NULL,
	`provider_key` text NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `sources` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`url` text NOT NULL,
	`title` text NOT NULL,
	`publisher` text NOT NULL,
	`published_at` text,
	`accessed_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`trust_score` integer DEFAULT 0 NOT NULL,
	`license_note` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `source_org_url_uq` ON `sources` (`organization_id`,`url`);--> statement-breakpoint
ALTER TABLE `blocked_topics` ADD `normalized_term` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `blocked_topics` ADD `active` integer DEFAULT true NOT NULL;--> statement-breakpoint
ALTER TABLE `blocked_topics` ADD `created_by` text REFERENCES users(id);--> statement-breakpoint
CREATE UNIQUE INDEX `blocked_org_term_kind_uq` ON `blocked_topics` (`organization_id`,`normalized_term`,`kind`);--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `created_by` text REFERENCES users(id);--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `mode` text DEFAULT 'manual' NOT NULL;--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `content_promise` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `narrative_structure` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `key_information` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `call_to_action` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `visual_suggestion` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `duration_seconds` integer DEFAULT 45 NOT NULL;--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `target_audience` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `objective` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `content_ideas` ADD `provider_key` text;--> statement-breakpoint
ALTER TABLE `content_niches` ADD `slug` text DEFAULT 'custom' NOT NULL;--> statement-breakpoint
ALTER TABLE `content_niches` ADD `description` text;--> statement-breakpoint
ALTER TABLE `content_niches` ADD `is_custom` integer DEFAULT false NOT NULL;--> statement-breakpoint
CREATE UNIQUE INDEX `niche_org_slug_uq` ON `content_niches` (`organization_id`,`slug`);--> statement-breakpoint
ALTER TABLE `scripts` ADD `created_by` text REFERENCES users(id);--> statement-breakpoint
ALTER TABLE `scripts` ADD `style` text DEFAULT 'documentary' NOT NULL;--> statement-breakpoint
ALTER TABLE `scripts` ADD `status` text DEFAULT 'draft' NOT NULL;--> statement-breakpoint
ALTER TABLE `scripts` ADD `moderation_status` text DEFAULT 'pending' NOT NULL;--> statement-breakpoint
ALTER TABLE `scripts` ADD `provider_key` text;