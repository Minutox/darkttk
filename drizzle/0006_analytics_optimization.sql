CREATE TABLE `publication_metric_snapshots` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`publication_job_id` text NOT NULL,
	`provider_video_id` text NOT NULL,
	`view_count` integer DEFAULT 0 NOT NULL,
	`like_count` integer DEFAULT 0 NOT NULL,
	`comment_count` integer DEFAULT 0 NOT NULL,
	`share_count` integer DEFAULT 0 NOT NULL,
	`source` text DEFAULT 'display_api' NOT NULL,
	`is_mock` integer DEFAULT false NOT NULL,
	`collected_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`publication_job_id`) REFERENCES `publication_jobs`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE TABLE `account_metric_snapshots` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`connection_id` text NOT NULL,
	`follower_count` integer DEFAULT 0 NOT NULL,
	`following_count` integer DEFAULT 0 NOT NULL,
	`likes_count` integer DEFAULT 0 NOT NULL,
	`video_count` integer DEFAULT 0 NOT NULL,
	`source` text DEFAULT 'display_api' NOT NULL,
	`is_mock` integer DEFAULT false NOT NULL,
	`collected_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`connection_id`) REFERENCES `tiktok_connections`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE TABLE `retention_observations` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`publication_job_id` text NOT NULL,
	`imported_by` text NOT NULL,
	`source` text NOT NULL,
	`average_watch_time_seconds` real,
	`completion_rate` real,
	`watched_full_rate` real,
	`saved_count` integer,
	`curve_json` text DEFAULT '[]' NOT NULL,
	`collected_at` text NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`publication_job_id`) REFERENCES `publication_jobs`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`imported_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE TABLE `analytics_recommendations` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`kind` text NOT NULL,
	`title` text NOT NULL,
	`rationale` text NOT NULL,
	`confidence` integer NOT NULL,
	`evidence_hash` text NOT NULL,
	`evidence_json` text DEFAULT '{}' NOT NULL,
	`status` text DEFAULT 'open' NOT NULL,
	`decided_by` text,
	`decided_at` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`decided_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `recommendation_org_evidence_uq` ON `analytics_recommendations` (`organization_id`,`evidence_hash`);--> statement-breakpoint
CREATE TABLE `content_experiments` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`created_by` text NOT NULL,
	`name` text NOT NULL,
	`hypothesis` text NOT NULL,
	`variable` text NOT NULL,
	`primary_metric` text NOT NULL,
	`status` text DEFAULT 'draft' NOT NULL,
	`started_at` text,
	`completed_at` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE TABLE `experiment_variants` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`experiment_id` text NOT NULL,
	`video_project_id` text NOT NULL,
	`label` text NOT NULL,
	`variable_value` text NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`experiment_id`) REFERENCES `content_experiments`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`video_project_id`) REFERENCES `video_projects`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `experiment_variant_label_uq` ON `experiment_variants` (`experiment_id`,`label`);--> statement-breakpoint
CREATE UNIQUE INDEX `experiment_variant_project_uq` ON `experiment_variants` (`experiment_id`,`video_project_id`);
