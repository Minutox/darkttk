import { integer, real, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";
import { sql } from "drizzle-orm";

const timestamps = {
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
};

export const organizations = sqliteTable("organizations", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  slug: text("slug").notNull().unique(),
  status: text("status", { enum: ["active", "suspended"] }).notNull().default("active"),
  ...timestamps,
});

export const users = sqliteTable("users", {
  id: text("id").primaryKey(),
  email: text("email").notNull().unique(),
  displayName: text("display_name").notNull(),
  status: text("status", { enum: ["active", "invited", "disabled"] }).notNull().default("active"),
  ...timestamps,
});

export const organizationMembers = sqliteTable(
  "organization_members",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    userId: text("user_id").notNull().references(() => users.id),
    role: text("role", { enum: ["admin", "manager", "editor", "reviewer", "analyst", "viewer"] }).notNull(),
    ...timestamps,
  },
  (table) => [uniqueIndex("member_org_user_uq").on(table.organizationId, table.userId)],
);

export const contentNiches = sqliteTable(
  "content_niches",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    name: text("name").notNull(),
    slug: text("slug").notNull().default("custom"),
    description: text("description"),
    enabled: integer("enabled", { mode: "boolean" }).notNull().default(true),
    isCustom: integer("is_custom", { mode: "boolean" }).notNull().default(false),
    ...timestamps,
  },
  (table) => [uniqueIndex("niche_org_slug_uq").on(table.organizationId, table.slug)],
);

export const blockedTopics = sqliteTable(
  "blocked_topics",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    term: text("term").notNull(),
    normalizedTerm: text("normalized_term").notNull().default(""),
    kind: text("kind", { enum: ["keyword", "topic", "category"] }).notNull(),
    active: integer("active", { mode: "boolean" }).notNull().default(true),
    createdBy: text("created_by").references(() => users.id),
    ...timestamps,
  },
  (table) => [
    uniqueIndex("blocked_org_term_kind_uq").on(
      table.organizationId,
      table.normalizedTerm,
      table.kind,
    ),
  ],
);

export const contentIdeas = sqliteTable("content_ideas", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  nicheId: text("niche_id").references(() => contentNiches.id),
  createdBy: text("created_by").references(() => users.id),
  mode: text("mode").notNull().default("manual"),
  title: text("title").notNull(),
  angle: text("angle").notNull(),
  contentPromise: text("content_promise").notNull().default(""),
  hook: text("hook").notNull(),
  narrativeStructure: text("narrative_structure").notNull().default(""),
  keyInformation: text("key_information").notNull().default(""),
  callToAction: text("call_to_action").notNull().default(""),
  visualSuggestion: text("visual_suggestion").notNull().default(""),
  durationSeconds: integer("duration_seconds").notNull().default(45),
  targetAudience: text("target_audience").notNull().default(""),
  objective: text("objective").notNull().default(""),
  status: text("status", { enum: ["draft", "selected", "rejected", "archived"] }).notNull().default("draft"),
  riskLevel: text("risk_level", { enum: ["low", "medium", "high", "blocked"] }).notNull().default("low"),
  providerKey: text("provider_key"),
  ...timestamps,
});

export const scripts = sqliteTable("scripts", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  ideaId: text("idea_id").notNull().references(() => contentIdeas.id),
  createdBy: text("created_by").references(() => users.id),
  version: integer("version").notNull().default(1),
  style: text("style").notNull().default("documentary"),
  content: text("content").notNull(),
  status: text("status").notNull().default("draft"),
  moderationStatus: text("moderation_status", { enum: ["pending", "verified", "needs_review", "blocked"] }).notNull().default("pending"),
  factCheckStatus: text("fact_check_status", { enum: ["pending", "verified", "needs_review", "blocked"] }).notNull().default("pending"),
  providerKey: text("provider_key"),
  ...timestamps,
});

export const aiProviders = sqliteTable(
  "ai_providers",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    capability: text("capability").notNull(),
    providerKey: text("provider_key").notNull(),
    displayName: text("display_name").notNull(),
    enabled: integer("enabled", { mode: "boolean" }).notNull().default(false),
    isMock: integer("is_mock", { mode: "boolean" }).notNull().default(true),
    configJson: text("config_json").notNull().default("{}"),
    secretRef: text("secret_ref"),
    ...timestamps,
  },
  (table) => [
    uniqueIndex("provider_org_capability_key_uq").on(
      table.organizationId,
      table.capability,
      table.providerKey,
    ),
  ],
);

export const sources = sqliteTable(
  "sources",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    url: text("url").notNull(),
    title: text("title").notNull(),
    publisher: text("publisher").notNull(),
    publishedAt: text("published_at"),
    accessedAt: text("accessed_at").notNull().default(sql`CURRENT_TIMESTAMP`),
    trustScore: integer("trust_score").notNull().default(0),
    licenseNote: text("license_note"),
    ...timestamps,
  },
  (table) => [uniqueIndex("source_org_url_uq").on(table.organizationId, table.url)],
);

export const factChecks = sqliteTable("fact_checks", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  scriptId: text("script_id").notNull().references(() => scripts.id),
  sourceId: text("source_id").references(() => sources.id),
  claim: text("claim").notNull(),
  verdict: text("verdict").notNull(),
  confidence: integer("confidence").notNull().default(0),
  evidence: text("evidence").notNull(),
  providerKey: text("provider_key").notNull(),
  reviewedBy: text("reviewed_by").references(() => users.id),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const scriptSources = sqliteTable(
  "script_sources",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    scriptId: text("script_id").notNull().references(() => scripts.id),
    sourceId: text("source_id").notNull().references(() => sources.id),
    createdBy: text("created_by").references(() => users.id),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [uniqueIndex("script_source_uq").on(table.scriptId, table.sourceId)],
);

export const moderationChecks = sqliteTable("moderation_checks", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  subjectType: text("subject_type").notNull(),
  subjectId: text("subject_id").notNull(),
  stage: text("stage").notNull(),
  result: text("result", { enum: ["allow", "review", "block"] }).notNull(),
  matchedRulesJson: text("matched_rules_json").notNull().default("[]"),
  policyVersion: text("policy_version").notNull(),
  providerKey: text("provider_key").notNull(),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const contentEvents = sqliteTable("content_events", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  actorId: text("actor_id").references(() => users.id),
  subjectType: text("subject_type").notNull(),
  subjectId: text("subject_id").notNull(),
  eventType: text("event_type").notNull(),
  payloadJson: text("payload_json").notNull().default("{}"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const videoProjects = sqliteTable("video_projects", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  scriptId: text("script_id").notNull().references(() => scripts.id),
  createdBy: text("created_by").references(() => users.id),
  voiceProfileId: text("voice_profile_id"),
  narrationAssetId: text("narration_asset_id"),
  captionTrackId: text("caption_track_id"),
  title: text("title").notNull(),
  status: text("status", { enum: ["draft", "assembling", "queued", "rendering", "preview_mock", "review", "changes_requested", "rejected", "approved", "scheduled", "published", "failed", "archived"] }).notNull().default("draft"),
  width: integer("width").notNull().default(1080),
  height: integer("height").notNull().default(1920),
  fps: integer("fps").notNull().default(30),
  durationMs: integer("duration_ms"),
  templateKey: text("template_key").notNull().default("dark-minimal-v1"),
  previewManifestJson: text("preview_manifest_json"),
  ...timestamps,
});

export const renderJobs = sqliteTable("render_jobs", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  videoProjectId: text("video_project_id").notNull().references(() => videoProjects.id),
  requestedBy: text("requested_by").references(() => users.id),
  idempotencyKey: text("idempotency_key").notNull().unique(),
  payloadHash: text("payload_hash").notNull().default(""),
  status: text("status", { enum: ["queued", "running", "mock_ready", "succeeded", "failed", "dispatch_failed", "dead_letter"] }).notNull().default("queued"),
  progress: integer("progress").notNull().default(0),
  attempts: integer("attempts").notNull().default(0),
  outputAssetId: text("output_asset_id"),
  errorCode: text("error_code"),
  errorMessage: text("error_message"),
  ...timestamps,
});

export const voiceProfiles = sqliteTable(
  "voice_profiles",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    createdBy: text("created_by").references(() => users.id),
    name: text("name").notNull(),
    providerKey: text("provider_key").notNull(),
    providerVoiceId: text("provider_voice_id").notNull(),
    genderLabel: text("gender_label"),
    language: text("language").notNull().default("pt-BR"),
    speakingRate: integer("speaking_rate").notNull().default(100),
    pitch: integer("pitch").notNull().default(0),
    emotion: text("emotion").notNull().default("neutral"),
    isMock: integer("is_mock", { mode: "boolean" }).notNull().default(true),
    active: integer("active", { mode: "boolean" }).notNull().default(true),
    consentReference: text("consent_reference"),
    ...timestamps,
  },
  (table) => [uniqueIndex("voice_org_name_uq").on(table.organizationId, table.name)],
);

export const mediaAssets = sqliteTable(
  "media_assets",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    createdBy: text("created_by").references(() => users.id),
    kind: text("kind").notNull(),
    origin: text("origin").notNull(),
    originalFilename: text("original_filename").notNull(),
    storageKey: text("storage_key").notNull().unique(),
    mimeType: text("mime_type").notNull(),
    sizeBytes: integer("size_bytes").notNull(),
    sha256: text("sha256").notNull(),
    durationMs: integer("duration_ms"),
    width: integer("width"),
    height: integer("height"),
    status: text("status").notNull().default("ready"),
    providerKey: text("provider_key"),
    isMock: integer("is_mock", { mode: "boolean" }).notNull().default(false),
    ...timestamps,
  },
  (table) => [uniqueIndex("asset_org_sha_uq").on(table.organizationId, table.sha256)],
);

export const mediaLicenses = sqliteTable("media_licenses", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  assetId: text("asset_id").notNull().references(() => mediaAssets.id).unique(),
  licenseType: text("license_type").notNull(),
  sourceUrl: text("source_url"),
  attribution: text("attribution"),
  validFrom: text("valid_from"),
  validUntil: text("valid_until"),
  proofStorageKey: text("proof_storage_key"),
  status: text("status").notNull().default("valid"),
  reviewedBy: text("reviewed_by").references(() => users.id),
  ...timestamps,
});

export const captionTracks = sqliteTable("caption_tracks", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  scriptId: text("script_id").notNull().references(() => scripts.id),
  createdBy: text("created_by").references(() => users.id),
  language: text("language").notNull().default("pt-BR"),
  style: text("style").notNull().default("dynamic"),
  status: text("status").notNull().default("draft"),
  safeAreaJson: text("safe_area_json").notNull().default('{"top":180,"right":80,"bottom":320,"left":80}'),
  ...timestamps,
});

export const captionCues = sqliteTable(
  "caption_cues",
  {
    id: text("id").primaryKey(),
    trackId: text("track_id").notNull().references(() => captionTracks.id),
    sequence: integer("sequence").notNull(),
    startMs: integer("start_ms").notNull(),
    endMs: integer("end_ms").notNull(),
    text: text("text").notNull(),
    highlightWordsJson: text("highlight_words_json").notNull().default("[]"),
  },
  (table) => [uniqueIndex("caption_track_sequence_uq").on(table.trackId, table.sequence)],
);

export const videoScenes = sqliteTable(
  "video_scenes",
  {
    id: text("id").primaryKey(),
    videoProjectId: text("video_project_id").notNull().references(() => videoProjects.id),
    mediaAssetId: text("media_asset_id").references(() => mediaAssets.id),
    sequence: integer("sequence").notNull(),
    startMs: integer("start_ms").notNull(),
    endMs: integer("end_ms").notNull(),
    trimStartMs: integer("trim_start_ms").notNull().default(0),
    textOverlayJson: text("text_overlay_json").notNull().default("{}"),
    transition: text("transition").notNull().default("cut"),
    motion: text("motion").notNull().default("none"),
    ...timestamps,
  },
  (table) => [uniqueIndex("scene_project_sequence_uq").on(table.videoProjectId, table.sequence)],
);

export const approvalRequests = sqliteTable("approval_requests", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  videoProjectId: text("video_project_id").notNull().references(() => videoProjects.id),
  requestedBy: text("requested_by").notNull().references(() => users.id),
  decidedBy: text("decided_by").references(() => users.id),
  version: integer("version").notNull().default(1),
  status: text("status", { enum: ["pending", "approved", "rejected", "changes_requested", "cancelled"] }).notNull().default("pending"),
  requestNote: text("request_note"),
  decisionNote: text("decision_note"),
  decidedAt: text("decided_at"),
  reason: text("reason"),
  ...timestamps,
});

export const scheduledSlots = sqliteTable("scheduled_slots", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  videoProjectId: text("video_project_id").notNull().references(() => videoProjects.id),
  approvalRequestId: text("approval_request_id").references(() => approvalRequests.id),
  createdBy: text("created_by").references(() => users.id),
  scheduledFor: text("scheduled_for").notNull(),
  timezone: text("timezone").notNull().default("America/Sao_Paulo"),
  status: text("status", { enum: ["reserved", "ready", "publishing", "published", "failed", "cancelled"] }).notNull().default("reserved"),
  note: text("note"),
  ...timestamps,
});

export const approvalEvents = sqliteTable("approval_events", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  approvalRequestId: text("approval_request_id").notNull().references(() => approvalRequests.id),
  actorId: text("actor_id").notNull().references(() => users.id),
  eventType: text("event_type").notNull(),
  note: text("note"),
  payloadJson: text("payload_json").notNull().default("{}"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const notifications = sqliteTable("notifications", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  recipientId: text("recipient_id").notNull().references(() => users.id),
  kind: text("kind").notNull(),
  title: text("title").notNull(),
  message: text("message").notNull(),
  entityType: text("entity_type"),
  entityId: text("entity_id"),
  readAt: text("read_at"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const tiktokOauthStates = sqliteTable("tiktok_oauth_states", {
  id: text("id").primaryKey(),
  stateHash: text("state_hash").notNull().unique(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  userId: text("user_id").notNull().references(() => users.id),
  redirectAfter: text("redirect_after").notNull().default("/"),
  expiresAt: text("expires_at").notNull(),
  consumedAt: text("consumed_at"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const tiktokConnections = sqliteTable(
  "tiktok_connections",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    connectedBy: text("connected_by").notNull().references(() => users.id),
    openId: text("open_id").notNull(),
    displayName: text("display_name"),
    avatarUrl: text("avatar_url"),
    accessTokenCiphertext: text("access_token_ciphertext").notNull(),
    refreshTokenCiphertext: text("refresh_token_ciphertext").notNull(),
    scopesJson: text("scopes_json").notNull().default("[]"),
    accessExpiresAt: text("access_expires_at").notNull(),
    refreshExpiresAt: text("refresh_expires_at").notNull(),
    status: text("status").notNull().default("active"),
    isMock: integer("is_mock", { mode: "boolean" }).notNull().default(false),
    creatorInfoJson: text("creator_info_json"),
    creatorInfoFetchedAt: text("creator_info_fetched_at"),
    lastErrorCode: text("last_error_code"),
    ...timestamps,
  },
  (table) => [uniqueIndex("tiktok_org_open_id_uq").on(table.organizationId, table.openId)],
);

export const publicationJobs = sqliteTable("publication_jobs", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  videoProjectId: text("video_project_id").notNull().references(() => videoProjects.id),
  scheduledSlotId: text("scheduled_slot_id").notNull().references(() => scheduledSlots.id),
  connectionId: text("connection_id").notNull().references(() => tiktokConnections.id),
  requestedBy: text("requested_by").notNull().references(() => users.id),
  outputAssetId: text("output_asset_id").notNull().references(() => mediaAssets.id),
  idempotencyKey: text("idempotency_key").notNull().unique(),
  payloadHash: text("payload_hash").notNull(),
  publishMode: text("publish_mode").notNull().default("direct_post"),
  caption: text("caption").notNull().default(""),
  privacyLevel: text("privacy_level"),
  disableComment: integer("disable_comment", { mode: "boolean" }).notNull().default(true),
  disableDuet: integer("disable_duet", { mode: "boolean" }).notNull().default(true),
  disableStitch: integer("disable_stitch", { mode: "boolean" }).notNull().default(true),
  brandContentToggle: integer("brand_content_toggle", { mode: "boolean" }).notNull().default(false),
  brandOrganicToggle: integer("brand_organic_toggle", { mode: "boolean" }).notNull().default(false),
  isAigc: integer("is_aigc", { mode: "boolean" }).notNull().default(false),
  consentedAt: text("consented_at").notNull(),
  scheduledFor: text("scheduled_for").notNull(),
  status: text("status").notNull().default("queued"),
  publishId: text("publish_id"),
  postId: text("post_id"),
  attempts: integer("attempts").notNull().default(0),
  providerLogId: text("provider_log_id"),
  errorCode: text("error_code"),
  errorMessage: text("error_message"),
  isMock: integer("is_mock", { mode: "boolean" }).notNull().default(false),
  ...timestamps,
});

export const publicationEvents = sqliteTable("publication_events", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  publicationJobId: text("publication_job_id").notNull().references(() => publicationJobs.id),
  eventType: text("event_type").notNull(),
  payloadJson: text("payload_json").notNull().default("{}"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const tiktokWebhookReceipts = sqliteTable("tiktok_webhook_receipts", {
  id: text("id").primaryKey(),
  deliveryHash: text("delivery_hash").notNull().unique(),
  eventType: text("event_type").notNull(),
  openId: text("open_id"),
  payloadJson: text("payload_json").notNull(),
  processed: integer("processed", { mode: "boolean" }).notNull().default(false),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const publicationMetricSnapshots = sqliteTable("publication_metric_snapshots", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  publicationJobId: text("publication_job_id").notNull().references(() => publicationJobs.id),
  providerVideoId: text("provider_video_id").notNull(),
  viewCount: integer("view_count").notNull().default(0),
  likeCount: integer("like_count").notNull().default(0),
  commentCount: integer("comment_count").notNull().default(0),
  shareCount: integer("share_count").notNull().default(0),
  source: text("source").notNull().default("display_api"),
  isMock: integer("is_mock", { mode: "boolean" }).notNull().default(false),
  collectedAt: text("collected_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const accountMetricSnapshots = sqliteTable("account_metric_snapshots", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  connectionId: text("connection_id").notNull().references(() => tiktokConnections.id),
  followerCount: integer("follower_count").notNull().default(0),
  followingCount: integer("following_count").notNull().default(0),
  likesCount: integer("likes_count").notNull().default(0),
  videoCount: integer("video_count").notNull().default(0),
  source: text("source").notNull().default("display_api"),
  isMock: integer("is_mock", { mode: "boolean" }).notNull().default(false),
  collectedAt: text("collected_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const retentionObservations = sqliteTable("retention_observations", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  publicationJobId: text("publication_job_id").notNull().references(() => publicationJobs.id),
  importedBy: text("imported_by").notNull().references(() => users.id),
  source: text("source").notNull(),
  averageWatchTimeSeconds: real("average_watch_time_seconds"),
  completionRate: real("completion_rate"),
  watchedFullRate: real("watched_full_rate"),
  savedCount: integer("saved_count"),
  curveJson: text("curve_json").notNull().default("[]"),
  collectedAt: text("collected_at").notNull(),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const analyticsRecommendations = sqliteTable(
  "analytics_recommendations",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    kind: text("kind").notNull(),
    title: text("title").notNull(),
    rationale: text("rationale").notNull(),
    confidence: integer("confidence").notNull(),
    evidenceHash: text("evidence_hash").notNull(),
    evidenceJson: text("evidence_json").notNull().default("{}"),
    status: text("status").notNull().default("open"),
    decidedBy: text("decided_by").references(() => users.id),
    decidedAt: text("decided_at"),
    ...timestamps,
  },
  (table) => [uniqueIndex("recommendation_org_evidence_uq").on(table.organizationId, table.evidenceHash)],
);

export const contentExperiments = sqliteTable("content_experiments", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  createdBy: text("created_by").notNull().references(() => users.id),
  name: text("name").notNull(),
  hypothesis: text("hypothesis").notNull(),
  variable: text("variable").notNull(),
  primaryMetric: text("primary_metric").notNull(),
  status: text("status").notNull().default("draft"),
  startedAt: text("started_at"),
  completedAt: text("completed_at"),
  ...timestamps,
});

export const experimentVariants = sqliteTable(
  "experiment_variants",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    experimentId: text("experiment_id").notNull().references(() => contentExperiments.id),
    videoProjectId: text("video_project_id").notNull().references(() => videoProjects.id),
    label: text("label").notNull(),
    variableValue: text("variable_value").notNull(),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [
    uniqueIndex("experiment_variant_label_uq").on(table.experimentId, table.label),
    uniqueIndex("experiment_variant_project_uq").on(table.experimentId, table.videoProjectId),
  ],
);

export const auditLogs = sqliteTable("audit_logs", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  actorId: text("actor_id").references(() => users.id),
  action: text("action").notNull(),
  entityType: text("entity_type").notNull(),
  entityId: text("entity_id").notNull(),
  metadataJson: text("metadata_json").notNull().default("{}"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const operationalErrors = sqliteTable("operational_errors", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").references(() => organizations.id),
  service: text("service").notNull(),
  code: text("code").notNull(),
  severity: text("severity").notNull().default("error"),
  status: text("status").notNull().default("open"),
  messageSanitized: text("message_sanitized").notNull(),
  fingerprint: text("fingerprint").notNull(),
  requestId: text("request_id"),
  occurrences: integer("occurrences").notNull().default(1),
  correctiveAction: text("corrective_action"),
  resolvedBy: text("resolved_by").references(() => users.id),
  firstSeenAt: text("first_seen_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  lastSeenAt: text("last_seen_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  resolvedAt: text("resolved_at"),
});

export const costBudgets = sqliteTable(
  "cost_budgets",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    monthlyLimitCents: integer("monthly_limit_cents").notNull(),
    warningPercent: integer("warning_percent").notNull().default(80),
    hardStopEnabled: integer("hard_stop_enabled", { mode: "boolean" }).notNull().default(false),
    currency: text("currency").notNull().default("BRL"),
    updatedBy: text("updated_by").notNull().references(() => users.id),
    ...timestamps,
  },
  (table) => [uniqueIndex("cost_budget_org_uq").on(table.organizationId)],
);

export const costLedgerEntries = sqliteTable(
  "cost_ledger_entries",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    provider: text("provider").notNull(),
    category: text("category").notNull(),
    amountMicros: integer("amount_micros").notNull(),
    quantity: integer("quantity").notNull().default(1),
    unit: text("unit").notNull().default("operation"),
    sourceRef: text("source_ref").notNull(),
    isMock: integer("is_mock", { mode: "boolean" }).notNull().default(false),
    occurredAt: text("occurred_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [uniqueIndex("cost_org_source_uq").on(table.organizationId, table.sourceRef)],
);

export const backupRuns = sqliteTable("backup_runs", {
  id: text("id").primaryKey(),
  environment: text("environment").notNull(),
  kind: text("kind").notNull(),
  status: text("status").notNull(),
  storageKey: text("storage_key"),
  checksumSha256: text("checksum_sha256"),
  sizeBytes: integer("size_bytes"),
  startedAt: text("started_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  completedAt: text("completed_at"),
  errorCode: text("error_code"),
});

export const auditCheckpoints = sqliteTable("audit_checkpoints", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  createdBy: text("created_by").notNull().references(() => users.id),
  fromAt: text("from_at").notNull(),
  toAt: text("to_at").notNull(),
  entryCount: integer("entry_count").notNull(),
  digestSha256: text("digest_sha256").notNull(),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const passwordRecoveryTokens = sqliteTable("password_recovery_tokens", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull().references(() => users.id),
  tokenHash: text("token_hash").notNull().unique(),
  expiresAt: text("expires_at").notNull(),
  usedAt: text("used_at"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const mfaCredentials = sqliteTable(
  "mfa_credentials",
  {
    id: text("id").primaryKey(),
    userId: text("user_id").notNull().references(() => users.id),
    secretCiphertext: text("secret_ciphertext").notNull(),
    recoveryCodesJson: text("recovery_codes_json").notNull().default("[]"),
    enabled: integer("enabled", { mode: "boolean" }).notNull().default(false),
    confirmedAt: text("confirmed_at"),
    lastUsedStep: integer("last_used_step"),
    ...timestamps,
  },
  (table) => [uniqueIndex("mfa_user_uq").on(table.userId)],
);

export const trendSources = sqliteTable(
  "trend_sources",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    name: text("name").notNull(),
    connectorType: text("connector_type").notNull(),
    endpointUrl: text("endpoint_url"),
    termsUrl: text("terms_url").notNull(),
    authorizedAt: text("authorized_at").notNull(),
    enabled: integer("enabled", { mode: "boolean" }).notNull().default(true),
    ...timestamps,
  },
  (table) => [uniqueIndex("trend_source_org_name_uq").on(table.organizationId, table.name)],
);

export const trends = sqliteTable("trends", {
  id: text("id").primaryKey(),
  organizationId: text("organization_id").notNull().references(() => organizations.id),
  sourceId: text("source_id").notNull().references(() => trendSources.id),
  topic: text("topic").notNull(),
  category: text("category").notNull(),
  relevanceReason: text("relevance_reason").notNull(),
  growthPercent: real("growth_percent").notNull(),
  interestVolume: integer("interest_volume").notNull(),
  competition: text("competition").notNull(),
  retentionScore: integer("retention_score").notNull(),
  shareScore: integer("share_score").notNull(),
  sensitivityRisk: text("sensitivity_risk").notNull(),
  saturationRisk: text("saturation_risk").notNull(),
  suggestedApproach: text("suggested_approach").notNull(),
  likelyAudience: text("likely_audience").notNull(),
  validUntil: text("valid_until").notNull(),
  capturedAt: text("captured_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  ...timestamps,
});

export const contentSeries = sqliteTable(
  "content_series",
  {
    id: text("id").primaryKey(),
    organizationId: text("organization_id").notNull().references(() => organizations.id),
    nicheId: text("niche_id").references(() => contentNiches.id),
    createdBy: text("created_by").notNull().references(() => users.id),
    name: text("name").notNull(),
    description: text("description").notNull(),
    cadence: text("cadence").notNull(),
    targetEpisodeCount: integer("target_episode_count").notNull(),
    status: text("status").notNull().default("active"),
    ...timestamps,
  },
  (table) => [uniqueIndex("content_series_org_name_uq").on(table.organizationId, table.name)],
);
