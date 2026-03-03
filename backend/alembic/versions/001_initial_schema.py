"""Initial schema with all tables.

Revision ID: 001
Revises:
Create Date: 2026-02-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("image", sa.String(512), nullable=True),
        sa.Column("youtube_channel_id", sa.String(255), unique=True, nullable=True, index=True),
        sa.Column("youtube_channel_name", sa.String(255), nullable=True),
        sa.Column("youtube_tokens_encrypted", sa.Text, nullable=True),
        sa.Column("niche", sa.String(255), nullable=True),
        sa.Column("topics", JSON, nullable=True),
        sa.Column("settings", JSON, nullable=True),
        sa.Column("dna_vector_id", sa.String(255), nullable=True),
        sa.Column("dna_confidence", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Trends table
    op.create_table(
        "trends",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("source", sa.String(50), nullable=False, index=True),
        sa.Column("category", sa.String(255), nullable=True, index=True),
        sa.Column("relevance_score", sa.Float, nullable=True),
        sa.Column("velocity", sa.String(50), nullable=False, index=True),
        sa.Column("competition_level", sa.String(50), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("peak_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_data", JSON, nullable=True),
        sa.Column("related_topics", JSON, nullable=True),
        sa.Column("niche_angle", sa.Text, nullable=True),
        sa.Column("suggested_content_types", JSON, nullable=True),
        sa.Column("time_sensitivity", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Ideas table
    op.create_table(
        "ideas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("trend_id", UUID(as_uuid=True), sa.ForeignKey("trends.id"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("hook", sa.Text, nullable=True),
        sa.Column("angle", sa.Text, nullable=True),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("secondary_types", JSON, nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("estimated_performance", sa.String(50), nullable=True),
        sa.Column("difficulty", sa.String(50), nullable=True),
        sa.Column("key_points", JSON, nullable=True),
        sa.Column("differentiation", sa.Text, nullable=True),
        sa.Column("target_audience_segment", sa.String(255), nullable=True),
        sa.Column("suggested_publish_window", sa.String(255), nullable=True),
        sa.Column("trend_connection", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Content table
    op.create_table(
        "content",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False, index=True),
        sa.Column("status", sa.String(50), nullable=False, index=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("outline", JSON, nullable=True),
        sa.Column("seo_title", sa.String(500), nullable=True),
        sa.Column("seo_description", sa.Text, nullable=True),
        sa.Column("tags", JSON, nullable=True),
        sa.Column("idea_id", UUID(as_uuid=True), sa.ForeignKey("ideas.id"), nullable=True),
        sa.Column("parent_content_id", UUID(as_uuid=True), sa.ForeignKey("content.id"), nullable=True),
        sa.Column("metadata_json", JSON, nullable=True),
        sa.Column("vector_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Video Analytics table
    op.create_table(
        "video_analytics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("video_id", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("publish_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("views", sa.Integer, default=0, nullable=False),
        sa.Column("watch_time_hours", sa.Float, default=0.0, nullable=False),
        sa.Column("average_view_duration", sa.Float, default=0.0, nullable=False),
        sa.Column("average_percentage_viewed", sa.Float, default=0.0, nullable=False),
        sa.Column("impressions", sa.Integer, default=0, nullable=False),
        sa.Column("ctr", sa.Float, default=0.0, nullable=False),
        sa.Column("likes", sa.Integer, default=0, nullable=False),
        sa.Column("comments", sa.Integer, default=0, nullable=False),
        sa.Column("shares", sa.Integer, default=0, nullable=False),
        sa.Column("subscribers_gained", sa.Integer, default=0, nullable=False),
        sa.Column("subscribers_lost", sa.Integer, default=0, nullable=False),
        sa.Column("revenue", sa.Float, nullable=True),
        sa.Column("traffic_sources", JSON, nullable=True),
        sa.Column("audience_retention_curve", JSON, nullable=True),
        sa.Column("top_keywords", JSON, nullable=True),
        sa.Column("demographics", JSON, nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Media Kits table
    op.create_table(
        "media_kits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("subscriber_count", sa.Integer, nullable=True),
        sa.Column("total_views", sa.BigInteger, nullable=True),
        sa.Column("avg_views_per_video", sa.Integer, nullable=True),
        sa.Column("audience_demographics", JSON, nullable=True),
        sa.Column("growth_30d", sa.Float, nullable=True),
        sa.Column("growth_60d", sa.Float, nullable=True),
        sa.Column("growth_90d", sa.Float, nullable=True),
        sa.Column("avg_likes", sa.Float, nullable=True),
        sa.Column("avg_comments", sa.Float, nullable=True),
        sa.Column("avg_shares", sa.Float, nullable=True),
        sa.Column("engagement_rate", sa.Float, nullable=True),
        sa.Column("brand_safety_score", sa.Float, nullable=True),
        sa.Column("suggested_cpm", sa.Float, nullable=True),
        sa.Column("suggested_flat_rate", sa.Float, nullable=True),
        sa.Column("rate_card", JSON, nullable=True),
        sa.Column("top_videos", JSON, nullable=True),
        sa.Column("collaboration_formats", JSON, nullable=True),
        sa.Column("public_slug", sa.String(100), unique=True, nullable=True),
        sa.Column("pdf_url", sa.String(512), nullable=True),
        sa.Column("full_data", JSON, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("media_kits")
    op.drop_table("video_analytics")
    op.drop_table("content")
    op.drop_table("ideas")
    op.drop_table("trends")
    op.drop_table("users")
