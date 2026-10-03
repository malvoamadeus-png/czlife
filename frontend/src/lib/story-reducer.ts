import type { Chapter, StoryEvent, StoryNode, StorySnapshot } from "./types";

export type StoryClientState = {
  snapshot: StorySnapshot;
  tree: StoryNode[];
  liveSequence: number;
  liveChapterId: string | null;
  readingChapterId: string | null;
  connected: boolean;
  seenEvents: Set<string>;
};

export function createInitialState(snapshot: StorySnapshot, tree: StoryNode[]): StoryClientState {
  const latest = snapshot.chapters.at(-1)?.chapter_id || null;
  return {
    snapshot,
    tree,
    liveSequence: snapshot.latest_sequence,
    liveChapterId: snapshot.playback?.current_chapter_id || latest,
    readingChapterId: snapshot.playback?.current_chapter_id || latest,
    connected: false,
    seenEvents: new Set(),
  };
}

function updateChapter(chapters: Chapter[], chapterId: string, mutate: (chapter: Chapter) => Chapter): Chapter[] {
  const index = chapters.findIndex((chapter) => chapter.chapter_id === chapterId);
  if (index < 0) return chapters;
  const next = [...chapters];
  next[index] = mutate(next[index]);
  return next;
}

export function applyEvent(state: StoryClientState, event: StoryEvent): StoryClientState {
  if (state.seenEvents.has(event.event_id) || event.sequence <= state.liveSequence) return state;
  const seenEvents = new Set(state.seenEvents);
  seenEvents.add(event.event_id);
  const payload = event.payload;
  let chapters = state.snapshot.chapters;
  let playback = state.snapshot.playback;
  let liveChapterId = state.liveChapterId;
  if (event.event_type === "chapter_started") {
    liveChapterId = String(payload.chapter_id || event.chapter_id || "");
    playback = playback ? { ...playback, current_chapter_id: liveChapterId, current_node_id: String(payload.node_id || ""), state: "GENERATING_CHAPTER" } : playback;
  }
  if (event.event_type === "text_delta" && event.chapter_id) {
    const delta = String(payload.text || "");
    chapters = updateChapter(chapters, event.chapter_id, (chapter) => ({
      ...chapter,
      content: chapter.content + delta,
      committed_offset: chapter.committed_offset + delta.length,
      generation_status: "generating",
    }));
  }
  if (event.event_type === "chapter_completed" && event.chapter_id) {
    chapters = updateChapter(chapters, event.chapter_id, (chapter) => ({ ...chapter, generation_status: "completed" }));
  }
  if (event.event_type === "death" && playback) {
    playback = { ...playback, state: "DECISION_REVEAL" };
  }
  if (event.event_type === "story_completed" && playback) {
    playback = { ...playback, state: "COMPLETED" };
  }
  return {
    ...state,
    snapshot: { ...state.snapshot, chapters, playback, latest_sequence: event.sequence },
    liveSequence: event.sequence,
    liveChapterId,
    seenEvents,
  };
}

export function setConnected(state: StoryClientState, connected: boolean): StoryClientState {
  return { ...state, connected };
}

