import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("APP_SECRET", "test-secret-with-at-least-thirty-two-characters")
os.environ.setdefault("AUTO_CREATE_SCHEMA", "true")
os.environ.setdefault("MEDIA_ROOT", "./work/test-media")
os.environ.setdefault("RENDER_MODE", "mock")
os.environ.setdefault("TIKTOK_MODE", "mock")
os.environ.setdefault("ENCRYPTION_KEY", "test-provider-token-encryption-key")
os.environ.setdefault("WORKSPACE_IDENTITY_SECRET", "test-workspace-identity-secret-at-least-32")
os.environ.setdefault("ACCOUNT_DELIVERY_MODE", "mock")
