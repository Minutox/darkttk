ALTER TABLE `approval_requests` ADD `version` integer DEFAULT 1 NOT NULL;--> statement-breakpoint
ALTER TABLE `approval_requests` ADD `request_note` text;--> statement-breakpoint
ALTER TABLE `approval_requests` ADD `decision_note` text;--> statement-breakpoint
ALTER TABLE `approval_requests` ADD `decided_at` text;--> statement-breakpoint
ALTER TABLE `scheduled_slots` ADD `approval_request_id` text REFERENCES approval_requests(id);--> statement-breakpoint
ALTER TABLE `scheduled_slots` ADD `created_by` text REFERENCES users(id);--> statement-breakpoint
ALTER TABLE `scheduled_slots` ADD `note` text;--> statement-breakpoint
CREATE TABLE `approval_events` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`approval_request_id` text NOT NULL,
	`actor_id` text NOT NULL,
	`event_type` text NOT NULL,
	`note` text,
	`payload_json` text DEFAULT '{}' NOT NULL,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`approval_request_id`) REFERENCES `approval_requests`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`actor_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE INDEX `approval_events_request_created_idx` ON `approval_events` (`approval_request_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `notifications` (
	`id` text PRIMARY KEY NOT NULL,
	`organization_id` text NOT NULL,
	`recipient_id` text NOT NULL,
	`kind` text NOT NULL,
	`title` text NOT NULL,
	`message` text NOT NULL,
	`entity_type` text,
	`entity_id` text,
	`read_at` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY (`organization_id`) REFERENCES `organizations`(`id`) ON UPDATE no action ON DELETE no action,
	FOREIGN KEY (`recipient_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);--> statement-breakpoint
CREATE INDEX `notifications_recipient_read_idx` ON `notifications` (`recipient_id`,`read_at`,`created_at`);
