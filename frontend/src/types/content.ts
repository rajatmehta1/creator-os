export type ContentStatus = "idea" | "draft" | "review" | "optimized" | "published" | "archived";

export type ContentType =
  | "youtube_video"
  | "youtube_short"
  | "blog_post"
  | "twitter_thread"
  | "linkedin_post"
  | "newsletter"
  | "podcast_outline";

export interface Content {
  id: string;
  userId: string;
  title: string;
  contentType: ContentType;
  status: ContentStatus;
  body?: string;
  outline?: Record<string, unknown>;
  seoTitle?: string;
  seoDescription?: string;
  tags: string[];
  ideaId?: string;
  parentContentId?: string;
  metadataJson: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface Idea {
  id: string;
  userId: string;
  title: string;
  hook?: string;
  angle?: string;
  contentType: string;
  secondaryTypes: string[];
  score?: number;
  estimatedPerformance?: string;
  difficulty?: string;
  keyPoints: string[];
  differentiation?: string;
  targetAudienceSegment?: string;
  suggestedPublishWindow?: string;
  trendConnection?: string;
  status: string;
  trendId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface SEOPackage {
  titleOptions: Array<{ title: string; ctrScore: number }>;
  description: string;
  tags: string[];
  hashtags: string[];
  chapters: Array<{ time: string; title: string }>;
  thumbnailConcepts: Array<{ description: string; text: string; emotion: string }>;
  metaTitle: string;
  metaDescription: string;
  suggestedHeaders: string[];
  targetWordCount: number;
  threadHooks: string[];
  hashtagStrategy: string[];
  subjectLines: Array<{ text: string; predictedOpenRate: number }>;
  previewText: string;
  primaryKeyword: string;
  secondaryKeywords: string[];
  searchVisibilityScore: number;
}
