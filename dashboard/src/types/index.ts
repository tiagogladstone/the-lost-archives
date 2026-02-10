export type StoryStatus =
  | "draft"
  | "scripting"
  | "producing"
  | "rendering"
  | "post_production"
  | "ready_for_review"
  | "publishing"
  | "published"
  | "failed";

export type Story = {
  id: string;
  topic: string;
  status: StoryStatus;
  style: string;
  aspect_ratio: string;
  created_at: string;
  updated_at: string;
};

export type Scene = {
  id: string;
  scene_order: number;
  text_content: string;
  image_url: string | null;
  audio_url: string | null;
  duration_seconds: number | null;
};

export type TitleOption = {
  id: string;
  title_text: string;
};

export type ThumbnailOption = {
  id: string;
  image_url: string;
  prompt: string | null;
};

export type StoryDetail = Story & {
  description: string | null;
  target_duration_minutes: number;
  languages: string[];
  script_text: string | null;
  scenes: Scene[];
  title_options: TitleOption[];
  thumbnail_options: ThumbnailOption[];
  selected_title: string | null;
  selected_thumbnail_url: string | null;
  video_url: string | null;
  youtube_url: string | null;
  metadata: Record<string, unknown>;
  error_message: string | null;
};

export type CreateStoryRequest = {
  topic: string;
  description?: string;
  target_duration_minutes?: number;
  languages?: string[];
  style?: string;
  aspect_ratio?: string;
};

export type ReviewData = {
  story_id: string;
  video_url: string | null;
  title_options: TitleOption[];
  thumbnail_options: ThumbnailOption[];
  metadata: Record<string, unknown>;
};

export type SelectReviewRequest = {
  title_option_id: string;
  thumbnail_option_id: string;
};
