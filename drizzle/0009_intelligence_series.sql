CREATE TABLE `trend_sources` (
  `id` text PRIMARY KEY NOT NULL,
  `organization_id` text NOT NULL,
  `name` text NOT NULL,
  `connector_type` text NOT NULL,
  `endpoint_url` text,
  `terms_url` text NOT NULL,
  `authorized_at` text NOT NULL,
  `enabled` integer DEFAULT true NOT NULL,
  `created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  `updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE cascade
);--> statement-breakpoint
CREATE UNIQUE INDEX `trend_source_org_name_uq` ON `trend_sources` (`organization_id`,`name`);--> statement-breakpoint
CREATE TABLE `trends` (
  `id` text PRIMARY KEY NOT NULL,
  `organization_id` text NOT NULL,
  `source_id` text NOT NULL,
  `topic` text NOT NULL,
  `category` text NOT NULL,
  `relevance_reason` text NOT NULL,
  `growth_percent` real NOT NULL,
  `interest_volume` integer NOT NULL,
  `competition` text NOT NULL,
  `retention_score` integer NOT NULL,
  `share_score` integer NOT NULL,
  `sensitivity_risk` text NOT NULL,
  `saturation_risk` text NOT NULL,
  `suggested_approach` text NOT NULL,
  `likely_audience` text NOT NULL,
  `valid_until` text NOT NULL,
  `captured_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  `created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  `updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE cascade,
  FOREIGN KEY (`source_id`) REFERENCES `trend_sources`(`id`) ON UPDATE no action ON DELETE restrict
);--> statement-breakpoint
CREATE INDEX `trends_org_captured_idx` ON `trends` (`organization_id`,`captured_at`);--> statement-breakpoint
CREATE INDEX `trends_source_topic_idx` ON `trends` (`source_id`,`topic`);--> statement-breakpoint
CREATE TABLE `content_series` (
  `id` text PRIMARY KEY NOT NULL,
  `organization_id` text NOT NULL,
  `niche_id` text,
  `created_by` text NOT NULL,
  `name` text NOT NULL,
  `description` text NOT NULL,
  `cadence` text NOT NULL,
  `target_episode_count` integer NOT NULL,
  `status` text DEFAULT 'active' NOT NULL,
  `created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  `updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE cascade,
  FOREIGN KEY (`niche_id`) REFERENCES `content_niches`(`id`) ON UPDATE no action ON DELETE set null,
  FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE restrict
);--> statement-breakpoint
CREATE UNIQUE INDEX `content_series_org_name_uq` ON `content_series` (`organization_id`,`name`);--> statement-breakpoint
CREATE INDEX `content_series_org_status_idx` ON `content_series` (`organization_id`,`status`);
