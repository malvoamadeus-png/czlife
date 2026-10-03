export type PlaybackState =
  | "RESEARCH_READY"
  | "PLANNING"
  | "VALIDATING"
  | "PLAN_LOCKED"
  | "GENERATING_CHAPTER"
  | "DECISION_REVEAL"
  | "PAUSED"
  | "COMPLETED";

export type StoryNode = {
  node_id: string;
  order: number;
  title: string;
  time_range: string;
  location: string;
  research_summary: string;
  source_refs: string[];
  visible_context: string;
  chapter_guidance: string;
  evidence_level: string;
  failure_routes: Array<{
    life_number: number;
    status: string;
    failure_node_id: string;
    death_reason: string;
    gained_memory: { title?: string; effect?: number } | null;
  }>;
};

export type Chapter = {
  chapter_id: string;
  life_number: number;
  node_id: string;
  chapter_index: number;
  chapter_title: string;
  generation_status: "pending" | "generating" | "completed" | "failed";
  content: string;
  committed_offset: number;
  completed_at: string | null;
};

export type StorySnapshot = {
  plan: {
    plan_id: string;
    version: number;
    title: string;
    ticker: string;
    status: PlaybackState;
    seed: number;
    rules_version: string;
    plan_hash: string | null;
    mainline_node_ids: string[];
    ending: { type: string; title: string; visible?: boolean };
  } | null;
  playback: {
    state: PlaybackState;
    current_route_index: number;
    current_chapter_id: string | null;
    current_node_id: string | null;
    current_life_number: number;
    latest_sequence: number;
    next_run_at: string | null;
    last_error: string | null;
  } | null;
  chapters: Chapter[];
  latest_sequence: number;
};

export type StoryEvent = {
  event_id: string;
  plan_version: number;
  sequence: number;
  chapter_id: string | null;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

