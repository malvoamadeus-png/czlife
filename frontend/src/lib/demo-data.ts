import type { StoryNode, StorySnapshot } from "./types";

export const fallbackSnapshot: StorySnapshot = {
  plan: {
    plan_id: "czlife-mvp",
    version: 1,
    title: "我的模拟首富路",
    ticker: "CZ 人生",
    status: "GENERATING_CHAPTER",
    seed: 1,
    rules_version: "route-v1",
    plan_hash: null,
    mainline_node_ids: ["N11", "N12", "N16", "N17", "N19", "N20", "N21", "N22"],
    ending: { type: "fictional", title: "首富结局", visible: true },
  },
  playback: {
    state: "GENERATING_CHAPTER",
    current_route_index: 0,
    current_chapter_id: "life-1-N11",
    current_node_id: "N11",
    current_life_number: 1,
    latest_sequence: 0,
    next_run_at: null,
    last_error: null,
  },
  chapters: [{
    chapter_id: "life-1-N11",
    life_number: 1,
    node_id: "N11",
    chapter_index: 1,
    chapter_title: "第一章：一条尚未命名的路",
    generation_status: "generating",
    content: "夜色落在屏幕上。一个念头从交易图表的缝隙里抬起头，等待下一次判定。",
    committed_offset: 42,
    completed_at: null,
  }],
  latest_sequence: 0,
};

export const fallbackTree: StoryNode[] = [
  ["N11", "决定创办 Binance", "2017"],
  ["N12", "发行 BNB 并完成 ICO", "2017-07"],
  ["N16", "Binance Chain 主网上线", "2019"],
  ["N17", "BNB 迁移到 Binance Chain", "2019"],
  ["N19", "BNB Smart Chain 主网上线", "2020-09"],
  ["N20", "宣布拟收购 FTX，随后撤回", "2022-11"],
  ["N21", "认罪并辞任 Binance CEO", "2023-11-21"],
  ["N22", "被判处四个月监禁", "2024-04-30"],
].map(([node_id, title, time_range], index) => ({
  node_id,
  title,
  time_range,
  order: index + 1,
  location: "",
  research_summary: "现实节点摘要加载中。",
  source_refs: [],
  visible_context: "",
  chapter_guidance: "",
  evidence_level: "primary-official",
  failure_routes: [],
}));

