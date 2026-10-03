import type { StoryEvent, StoryNode, StorySnapshot, Chapter } from "./types";

const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8820").replace(/\/$/, "");

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json() as Promise<T>;
}

export function fetchSnapshot(): Promise<StorySnapshot> {
  return request<StorySnapshot>("/v1/story/snapshot");
}

export function fetchTree(): Promise<{ plan_id: string; version: number; nodes: StoryNode[] }> {
  return request("/v1/story/tree");
}

export function fetchChapter(chapterId: string): Promise<Chapter> {
  return request(`/v1/story/chapters/${encodeURIComponent(chapterId)}`);
}

export function eventStreamUrl(after: number): string {
  return `${baseUrl}/v1/story/stream?after=${after}`;
}

export function parseEventMessage(event: MessageEvent<string>): StoryEvent | null {
  try {
    const parsed = JSON.parse(event.data) as StoryEvent;
    if (!parsed || typeof parsed.sequence !== "number") return null;
    return parsed;
  } catch {
    return null;
  }
}

