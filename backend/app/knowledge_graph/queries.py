"""Cypher query templates for the Creator OS knowledge graph.

All queries are plain string constants with ``$parameter`` placeholders
that the Neo4j driver substitutes at execution time.  Never interpolate
user input directly into these strings.
"""

# =====================================================================
# CREATE operations
# =====================================================================

CREATE_CREATOR: str = """
MERGE (c:Creator {creator_id: $creator_id})
ON CREATE SET
    c.name             = $name,
    c.niche            = $niche,
    c.youtube_channel_id = $youtube_channel_id,
    c.primary_topics   = $primary_topics,
    c.authority_score   = 0.0,
    c.content_count    = 0,
    c.created_at       = datetime(),
    c.updated_at       = datetime()
ON MATCH SET
    c.name             = $name,
    c.niche            = coalesce($niche, c.niche),
    c.youtube_channel_id = coalesce($youtube_channel_id, c.youtube_channel_id),
    c.primary_topics   = CASE WHEN size($primary_topics) > 0
                              THEN $primary_topics
                              ELSE c.primary_topics END,
    c.updated_at       = datetime()
RETURN c
"""

CREATE_CONTENT: str = """
MERGE (c:Content {content_id: $content_id})
ON CREATE SET
    c.title            = $title,
    c.content_type     = $content_type,
    c.status           = $status,
    c.word_count       = $word_count,
    c.vector_id        = $vector_id,
    c.url              = $url,
    c.published_at     = $published_at,
    c.performance_score = $performance_score,
    c.created_at       = datetime(),
    c.updated_at       = datetime()
ON MATCH SET
    c.title            = $title,
    c.content_type     = $content_type,
    c.status           = coalesce($status, c.status),
    c.word_count       = CASE WHEN $word_count > 0
                              THEN $word_count
                              ELSE c.word_count END,
    c.vector_id        = coalesce($vector_id, c.vector_id),
    c.url              = coalesce($url, c.url),
    c.performance_score = coalesce($performance_score, c.performance_score),
    c.updated_at       = datetime()
RETURN c
"""

CREATE_TOPIC: str = """
MERGE (t:Topic {name: toLower(trim($name))})
ON CREATE SET
    t.display_name     = $display_name,
    t.category         = $category,
    t.depth            = $depth,
    t.content_count    = 0,
    t.authority_score   = 0.0,
    t.created_at       = datetime(),
    t.updated_at       = datetime()
ON MATCH SET
    t.display_name     = coalesce($display_name, t.display_name),
    t.category         = coalesce($category, t.category),
    t.updated_at       = datetime()
RETURN t
"""

CREATE_KEYWORD: str = """
MERGE (k:Keyword {name: toLower(trim($name))})
ON CREATE SET
    k.search_volume    = $search_volume,
    k.competition      = $competition,
    k.cpc              = $cpc,
    k.intent           = $intent,
    k.created_at       = datetime(),
    k.updated_at       = datetime()
ON MATCH SET
    k.search_volume    = coalesce($search_volume, k.search_volume),
    k.competition      = coalesce($competition, k.competition),
    k.updated_at       = datetime()
RETURN k
"""

CREATE_TREND: str = """
MERGE (t:Trend {trend_id: $trend_id})
ON CREATE SET
    t.title            = $title,
    t.source           = $source,
    t.velocity         = $velocity,
    t.relevance_score  = $relevance_score,
    t.category         = $category,
    t.time_sensitivity = $time_sensitivity,
    t.detected_at      = datetime($detected_at),
    t.created_at       = datetime(),
    t.updated_at       = datetime()
ON MATCH SET
    t.velocity         = $velocity,
    t.relevance_score  = $relevance_score,
    t.updated_at       = datetime()
RETURN t
"""

CREATE_AUDIENCE_SEGMENT: str = """
MERGE (a:AudienceSegment {name: toLower(trim($name))})
ON CREATE SET
    a.description      = $description,
    a.size_estimate    = $size_estimate,
    a.engagement_level = $engagement_level,
    a.created_at       = datetime(),
    a.updated_at       = datetime()
ON MATCH SET
    a.description      = coalesce($description, a.description),
    a.updated_at       = datetime()
RETURN a
"""

CREATE_IDEA: str = """
MERGE (i:Idea {idea_id: $idea_id})
ON CREATE SET
    i.title                   = $title,
    i.hook                    = $hook,
    i.angle                   = $angle,
    i.content_type            = $content_type,
    i.score                   = $score,
    i.difficulty              = $difficulty,
    i.status                  = $status,
    i.target_audience_segment = $target_audience_segment,
    i.created_at              = datetime(),
    i.updated_at              = datetime()
ON MATCH SET
    i.status                  = coalesce($status, i.status),
    i.score                   = coalesce($score, i.score),
    i.updated_at              = datetime()
RETURN i
"""

# =====================================================================
# RELATIONSHIP operations
# =====================================================================

LINK_CONTENT_TO_TOPIC: str = """
MATCH (c:Content {content_id: $content_id})
MATCH (t:Topic {name: toLower(trim($topic_name))})
MERGE (c)-[r:COVERS]->(t)
ON CREATE SET
    r.relevance       = $relevance,
    r.is_primary      = $is_primary,
    r.mentioned_count = $mentioned_count,
    r.created_at      = datetime()
ON MATCH SET
    r.relevance       = $relevance,
    r.mentioned_count = r.mentioned_count + $mentioned_count,
    r.updated_at      = datetime()
WITH t
SET t.content_count = t.content_count + 1,
    t.updated_at    = datetime()
RETURN t
"""

LINK_CREATOR_TO_TOPIC: str = """
MATCH (cr:Creator {creator_id: $creator_id})
MATCH (t:Topic {name: toLower(trim($topic_name))})
MERGE (cr)-[r:HAS_AUTHORITY]->(t)
ON CREATE SET
    r.score            = $authority_score,
    r.content_count    = 1,
    r.first_covered_at = datetime(),
    r.last_covered_at  = datetime()
ON MATCH SET
    r.score            = $authority_score,
    r.content_count    = r.content_count + 1,
    r.last_covered_at  = datetime()
RETURN cr, t, r
"""

LINK_CONTENT_TO_CREATOR: str = """
MATCH (c:Content {content_id: $content_id})
MATCH (cr:Creator {creator_id: $creator_id})
MERGE (c)-[r:CREATED_BY]->(cr)
ON CREATE SET r.created_at = datetime()
RETURN c, cr
"""

LINK_CONTENT_TO_KEYWORD: str = """
MATCH (c:Content {content_id: $content_id})
MATCH (k:Keyword {name: toLower(trim($keyword_name))})
MERGE (c)-[r:TARGETS]->(k)
ON CREATE SET r.created_at = datetime()
RETURN c, k
"""

LINK_KEYWORD_TO_TOPIC: str = """
MATCH (k:Keyword {name: toLower(trim($keyword_name))})
MATCH (t:Topic {name: toLower(trim($topic_name))})
MERGE (k)-[r:KEYWORD_OF]->(t)
ON CREATE SET r.created_at = datetime()
RETURN k, t
"""

LINK_TOPIC_PARENT: str = """
MATCH (child:Topic {name: toLower(trim($child_name))})
MATCH (parent:Topic {name: toLower(trim($parent_name))})
MERGE (child)-[r:SUBTOPIC_OF]->(parent)
ON CREATE SET r.created_at = datetime()
RETURN child, parent
"""

LINK_IDEA_TO_TREND: str = """
MATCH (i:Idea {idea_id: $idea_id})
MATCH (t:Trend {trend_id: $trend_id})
MERGE (i)-[r:INSPIRED_BY]->(t)
ON CREATE SET r.created_at = datetime()
RETURN i, t
"""

LINK_IDEA_TO_TOPIC: str = """
MATCH (i:Idea {idea_id: $idea_id})
MATCH (t:Topic {name: toLower(trim($topic_name))})
MERGE (i)-[r:COVERS]->(t)
ON CREATE SET r.created_at = datetime()
RETURN i, t
"""

# =====================================================================
# ANALYSIS queries
# =====================================================================

FIND_CONTENT_GAPS: str = """
// Topics the creator has authority on but no recent content (>30 days).
MATCH (cr:Creator {creator_id: $creator_id})-[auth:HAS_AUTHORITY]->(t:Topic)
WHERE auth.score > 0
OPTIONAL MATCH (c:Content)-[:COVERS]->(t)
    WHERE c.content_id IS NOT NULL
      AND c.created_at > datetime() - duration({days: 30})
WITH t, auth, collect(c) AS recent_content
WHERE size(recent_content) = 0
RETURN t.name           AS topic,
       t.display_name   AS display_name,
       auth.score       AS authority_score,
       t.content_count  AS total_content_count,
       auth.last_covered_at AS last_covered
ORDER BY auth.score DESC
LIMIT $limit
"""

FIND_COMPOUNDING_OPPORTUNITIES: str = """
// Topics with growing content counts that could benefit from deep dives
// or series content.  Identifies clusters where adding more content
// would compound existing authority.
MATCH (cr:Creator {creator_id: $creator_id})-[auth:HAS_AUTHORITY]->(t:Topic)
WHERE auth.content_count >= 2
OPTIONAL MATCH (t)<-[:SUBTOPIC_OF]-(sub:Topic)<-[:COVERS]-(c:Content)-[:CREATED_BY]->(cr)
WITH t, auth,
     count(DISTINCT sub)   AS sub_topic_count,
     count(DISTINCT c)     AS sub_content_count,
     auth.score            AS current_authority,
     auth.content_count    AS direct_content_count
WHERE direct_content_count + sub_content_count >= $min_pieces
RETURN t.name              AS topic,
       t.display_name      AS display_name,
       current_authority    AS authority_score,
       direct_content_count AS direct_pieces,
       sub_content_count   AS sub_pieces,
       sub_topic_count     AS sub_topics,
       direct_content_count + sub_content_count AS total_pieces,
       current_authority * (1 + log(direct_content_count + sub_content_count))
           AS compounding_score
ORDER BY compounding_score DESC
LIMIT $limit
"""

TOPIC_AUTHORITY_SCORE: str = """
// Calculate a creator's authority score on a single topic.
// Considers: number of pieces, recency, subtopic coverage, and
// content performance.
MATCH (cr:Creator {creator_id: $creator_id})-[auth:HAS_AUTHORITY]->(t:Topic {name: toLower(trim($topic_name))})
OPTIONAL MATCH (c:Content)-[:COVERS]->(t)
    WHERE (c)-[:CREATED_BY]->(cr)
WITH cr, t, auth,
     count(c)                                     AS piece_count,
     avg(coalesce(c.performance_score, 50.0))      AS avg_performance,
     max(c.created_at)                             AS latest_piece
OPTIONAL MATCH (t)<-[:SUBTOPIC_OF]-(sub:Topic)<-[:COVERS]-(sc:Content)-[:CREATED_BY]->(cr)
WITH t, auth, piece_count, avg_performance, latest_piece,
     count(DISTINCT sub) AS subtopics_covered
RETURN t.name                 AS topic,
       piece_count,
       subtopics_covered,
       avg_performance,
       latest_piece,
       // weighted score formula
       (piece_count * 10)
       + (subtopics_covered * 15)
       + (avg_performance * 0.5)
       + CASE WHEN latest_piece > datetime() - duration({days: 14}) THEN 20
              WHEN latest_piece > datetime() - duration({days: 30}) THEN 10
              ELSE 0 END      AS authority_score
"""

# =====================================================================
# READ / MAP queries
# =====================================================================

FIND_RELATED_TOPICS: str = """
// Find topics related to a given topic through shared content, subtopic
// relationships, or shared keywords.
MATCH (t:Topic {name: toLower(trim($topic_name))})
OPTIONAL MATCH (t)<-[:COVERS]-(c:Content)-[:COVERS]->(related:Topic)
    WHERE related.name <> t.name
OPTIONAL MATCH (t)<-[:SUBTOPIC_OF]-(child:Topic)
OPTIONAL MATCH (t)-[:SUBTOPIC_OF]->(parent:Topic)
OPTIONAL MATCH (t)<-[:KEYWORD_OF]-(k:Keyword)-[:KEYWORD_OF]->(kt:Topic)
    WHERE kt.name <> t.name
WITH t,
     collect(DISTINCT related.name) AS via_content,
     collect(DISTINCT child.name)   AS children,
     collect(DISTINCT parent.name)  AS parents,
     collect(DISTINCT kt.name)      AS via_keywords
RETURN t.name          AS topic,
       via_content,
       children,
       parents,
       via_keywords,
       size(via_content) + size(children) + size(parents) + size(via_keywords)
           AS connection_strength
"""

GET_CREATOR_TOPIC_MAP: str = """
// Full topic authority map for a creator.
MATCH (cr:Creator {creator_id: $creator_id})-[auth:HAS_AUTHORITY]->(t:Topic)
OPTIONAL MATCH (t)<-[:SUBTOPIC_OF]-(sub:Topic)
RETURN t.name            AS topic,
       t.display_name    AS display_name,
       t.category        AS category,
       auth.score        AS authority_score,
       auth.content_count AS content_count,
       auth.first_covered_at AS first_covered,
       auth.last_covered_at  AS last_covered,
       collect(sub.name) AS subtopics
ORDER BY auth.score DESC
"""

GET_CONTENT_MAP: str = """
// Content map for a creator showing all content and its topic connections.
MATCH (cr:Creator {creator_id: $creator_id})<-[:CREATED_BY]-(c:Content)
OPTIONAL MATCH (c)-[r:COVERS]->(t:Topic)
OPTIONAL MATCH (c)-[:TARGETS]->(k:Keyword)
RETURN c.content_id     AS content_id,
       c.title          AS title,
       c.content_type   AS content_type,
       c.status         AS status,
       c.created_at     AS created_at,
       c.performance_score AS performance_score,
       collect(DISTINCT {
           topic: t.name,
           relevance: r.relevance,
           is_primary: r.is_primary
       }) AS topics,
       collect(DISTINCT k.name) AS keywords
ORDER BY c.created_at DESC
LIMIT $limit
"""

# =====================================================================
# GRAPH PROXIMITY (used by hybrid search)
# =====================================================================

GRAPH_PROXIMITY_SEARCH: str = """
// Given a set of topic names, find content within N hops that is
// created by the specified creator.  Returns content IDs with a
// graph-based relevance score.
MATCH (cr:Creator {creator_id: $creator_id})<-[:CREATED_BY]-(c:Content)
MATCH (c)-[r:COVERS]->(t:Topic)
WHERE t.name IN $topic_names
WITH c, sum(r.relevance) AS direct_relevance, collect(t.name) AS matched_topics
// Also check 1-hop neighbours (subtopics / parent topics)
OPTIONAL MATCH (c)-[:COVERS]->(ot:Topic)-[:SUBTOPIC_OF*0..1]-(neighbour:Topic)
WHERE neighbour.name IN $topic_names AND NOT ot.name IN matched_topics
WITH c, direct_relevance,
     matched_topics,
     count(DISTINCT neighbour) AS neighbour_hits
RETURN c.content_id    AS content_id,
       c.title         AS title,
       c.content_type  AS content_type,
       c.vector_id     AS vector_id,
       matched_topics,
       direct_relevance + (neighbour_hits * 0.5) AS graph_score
ORDER BY graph_score DESC
LIMIT $limit
"""
