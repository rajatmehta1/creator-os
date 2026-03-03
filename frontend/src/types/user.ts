export interface User {
  id: string;
  email: string;
  name: string;
  image?: string;
  youtubeChannelId?: string;
  youtubeChannelName?: string;
  niche?: string;
  topics: string[];
  dnaConfidence?: number;
}

export interface UserProfile extends User {
  settings: Record<string, unknown>;
}

export interface CreatorDNA {
  vocabularyComplexity?: number;
  sentenceRhythm?: Record<string, number>;
  fillerWords: string[];
  signaturePhrases: string[];
  humorStyle?: string;
  humorFrequency?: number;
  topicClusters: Array<{ name: string; weight: number }>;
  expertiseDepth: Record<string, number>;
  formalityLevel?: number;
  audienceAddressStyle?: string;
  vulnerabilityLevel?: number;
  callToActionStyle?: string;
  preferredFormatLength: Record<string, number>;
  hookStyle?: string;
  pacingPattern?: string;
  storytellingFrequency?: number;
  confidenceScore?: number;
  lastUpdated?: string;
  videosAnalyzed: number;
}
