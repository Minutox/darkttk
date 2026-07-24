ALTER TABLE `video_projects` ADD `created_by` text REFERENCES users(id);--> statement-breakpoint
ALTER TABLE `video_projects` ADD `voice_profile_id` text;--> statement-breakpoint
ALTER TABLE `video_projects` ADD `narration_asset_id` text;--> statement-breakpoint
ALTER TABLE `video_projects` ADD `caption_track_id` text;--> statement-breakpoint
ALTER TABLE `video_projects` ADD `width` integer DEFAULT 1080 NOT NULL;--> statement-breakpoint
ALTER TABLE `video_projects` ADD `height` integer DEFAULT 1920 NOT NULL;--> statement-breakpoint
ALTER TABLE `video_projects` ADD `fps` integer DEFAULT 30 NOT NULL;--> statement-breakpoint
ALTER TABLE `video_projects` ADD `template_key` text DEFAULT 'dark-minimal-v1' NOT NULL;--> statement-breakpoint
ALTER TABLE `video_projects` ADD `preview_manifest_json` text;--> statement-breakpoint
ALTER TABLE `render_jobs` ADD `requested_by` text REFERENCES users(id);--> statement-breakpoint
ALTER TABLE `render_jobs` ADD `payload_hash` text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE `render_jobs` ADD `output_asset_id` text;--> statement-breakpoint
ALTER TABLE `render_jobs` ADD `error_message` text;--> statement-breakpoint
CREATE TABLE `voice_profiles` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`created_by` text,
	`name` text NOT NULL,
	`provider_key` text NOT NULL,
	`provider_voice_id` text NOT NULL,
	`gender_label` text,
	`language` text DEFAULT 'pt-BR' NOT NULL,
	`speaking_rate` integer DEFAULT 100 NOT NULL,
	`pitch` integer DEFAULT 0 NOT NULL,
	`emotion` text DEFAULT 'neutral' NOT NULL,
	`is_mock` integer DEFAULT true NOT NULL,
	`active` integer DEFAULT true NOT NULL,
	`consent_reference` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `voice_org_name_uq` ON `voice_profiles` (`organization_id`,`name`);--> statement-breakpoint
CREATE TABLE `media_assets` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`created_by` text,
	`kind` text NOT NULL,
	`origin` text NOT NULL,
	`original_filename` text NOT NULL,
	`storage_key` text NOT NULL,
	`mime_type` text NOT NULL,
	`size_bytes` integer NOT NULL,
	`sha256` text NOT NULL,
	`duration_ms` integer,
	`width` integer,
	`height` integer,
	`status` text DEFAULT 'ready' NOT NULL,
	`provider_key` text,
	`is_mock` integer DEFAULT false NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `media_assets_storage_key_unique` ON `media_assets` (`storage_key`);--> statement-breakpoint
CREATE UNIQUE INDEX `asset_org_sha_uq` ON `media_assets` (`organization_id`,`sha256`);--> statement-breakpoint
CREATE TABLE `media_licenses` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`asset_id` text NOT NULL,
	`license_type` text NOT NULL,
	`source_url` text,
	`attribution` text,
	`valid_from` text,
	`valid_until` text,
	`proof_storage_key` text,
	`status` text DEFAULT 'valid' NOT NULL,
	`reviewed_by` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`asset_id`) REFERENCES `media_assets`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`reviewed_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `media_licenses_asset_id_unique` ON `media_licenses` (`asset_id`);--> statement-breakpoint
CREATE TABLE `caption_tracks` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`script_id` text NOT NULL,
	`created_by` text,
	`language` text DEFAULT 'pt-BR' NOT NULL,
	`style` text DEFAULT 'dynamic' NOT NULL,
	`status` text DEFAULT 'draft' NOT NULL,
	`safe_area_json` text DEFAULT '{"top":180,"right":80,"bottom":320,"left":80}' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`script_id`) REFERENCES `scripts`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`created_by`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE TABLE `caption_cues` (
	`id` text PRIMARY KEY NOT NULL,
	`track_id` text NOT NULL,
	`sequence` integer NOT NULL,
	`start_ms` integer NOT NULL,
	`end_ms` integer NOT NULL,
	`text` text NOT NULL,
	`highlight_words_json` text DEFAULT '[]' NOT NULL,
	FOREIGN KEY (`track_id`) REFERENCES `caption_tracks`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `caption_track_sequence_uq` ON `caption_cues` (`track_id`,`sequence`);--> statement-breakpoint
CREATE TABLE `video_scenes` (
	`id` text PRIMARY KEY NOT NULL,
	`video_project_id` text NOT NULL,
	`media_asset_id` text,
	`sequence` integer NOT NULL,
	`start_ms` integer NOT NULL,
	`end_ms` integer NOT NULL,
	`trim_start_ms` integer DEFAULT 0 NOT NULL,
	`text_overlay_json` text DEFAULT '{}' NOT NULL,
	`transition` text DEFAULT 'cut' NOT NULL,
	`motion` text DEFAULT 'none' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	`updated_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`video_project_id`) REFERENCES `video_projects`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`media_asset_id`) REFERENCES `media_assets`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE UNIQUE INDEX `scene_project_sequence_uq` ON `video_scenes` (`video_project_id`,`sequence`);
