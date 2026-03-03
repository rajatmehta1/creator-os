// Creator OS - Neo4j Schema Initialization

// Constraints (unique IDs)
CREATE CONSTRAINT creator_id IF NOT EXISTS FOR (c:Creator) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT content_id IF NOT EXISTS FOR (c:Content) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT keyword_id IF NOT EXISTS FOR (k:Keyword) REQUIRE k.id IS UNIQUE;
CREATE CONSTRAINT trend_id IF NOT EXISTS FOR (t:Trend) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT audience_id IF NOT EXISTS FOR (a:AudienceSegment) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT idea_id IF NOT EXISTS FOR (i:Idea) REQUIRE i.id IS UNIQUE;

// Indexes for common queries
CREATE INDEX creator_channel IF NOT EXISTS FOR (c:Creator) ON (c.channel_id);
CREATE INDEX content_status IF NOT EXISTS FOR (c:Content) ON (c.status);
CREATE INDEX content_type IF NOT EXISTS FOR (c:Content) ON (c.content_type);
CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.name);
CREATE INDEX topic_category IF NOT EXISTS FOR (t:Topic) ON (t.category);
CREATE INDEX keyword_term IF NOT EXISTS FOR (k:Keyword) ON (k.term);
CREATE INDEX trend_status IF NOT EXISTS FOR (t:Trend) ON (t.status);
CREATE INDEX trend_velocity IF NOT EXISTS FOR (t:Trend) ON (t.velocity);
CREATE INDEX idea_status IF NOT EXISTS FOR (i:Idea) ON (i.status);
