"use client";

import "@xyflow/react/dist/style.css";

import { useCallback, useEffect, useMemo, useReducer, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Activity, ArrowUpRight, BookOpenText, GitBranch, Radio, Send, Sparkles, TerminalSquare, Wifi, WifiOff } from "lucide-react";
import { Background, Handle, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";

import { eventStreamUrl, fetchSnapshot, fetchTree, parseEventMessage } from "@/lib/api";
import { fallbackSnapshot, fallbackTree } from "@/lib/demo-data";
import { applyEvent, createInitialState, setConnected, type StoryClientState } from "@/lib/story-reducer";
import type { StoryEvent, StoryNode } from "@/lib/types";

type NodeData = { storyNode: StoryNode; active: boolean; visited: boolean; muted: boolean };

function TreeNode({ data }: NodeProps<Node<NodeData>>) {
  const { storyNode, active, visited, muted } = data;
  return (
    <motion.div
      className={`tree-node ${active ? "tree-node-active" : ""} ${visited ? "tree-node-visited" : ""} ${muted ? "tree-node-muted" : ""}`}
      animate={active ? { scale: [1, 1.025, 1], boxShadow: ["0 0 0 rgba(240,185,11,0)", "0 0 32px rgba(240,185,11,.28)", "0 0 0 rgba(240,185,11,0)"] } : {}}
      transition={{ duration: 2.4, repeat: active ? Infinity : 0 }}
    >
      <Handle type="target" position={Position.Left} className="tree-handle" />
      <div className="tree-node-top"><span>{storyNode.time_range}</span><span>{storyNode.node_id}</span></div>
      <div className="tree-node-title">{storyNode.title}</div>
      {storyNode.failure_routes.length > 0 && <div className="tree-node-failure">{storyNode.failure_routes.length} 条已发生分支</div>}
      <Handle type="source" position={Position.Right} className="tree-handle" />
    </motion.div>
  );
}

const nodeTypes = { story: TreeNode };

function StoryTree({ state, onSelect }: { state: StoryClientState; onSelect: (id: string) => void }) {
  const activeId = state.snapshot.playback?.current_node_id;
  const visited = useMemo(() => new Set(state.snapshot.chapters.map((chapter) => chapter.node_id)), [state.snapshot.chapters]);
  const nodes = useMemo<Node<NodeData>[]>(() => state.tree.map((storyNode, index) => ({
    id: storyNode.node_id,
    type: "story",
    position: { x: index * 224, y: 48 + ((index % 2) * 20) },
    data: { storyNode, active: storyNode.node_id === activeId, visited: visited.has(storyNode.node_id), muted: index > (state.snapshot.playback?.current_route_index || 0) + 2 },
    draggable: false,
  })), [activeId, state.snapshot.playback?.current_route_index, state.tree, visited]);
  const edges = useMemo<Edge[]>(() => state.tree.slice(1).map((storyNode, index) => ({
    id: `${state.tree[index].node_id}-${storyNode.node_id}`,
    source: state.tree[index].node_id,
    target: storyNode.node_id,
    type: "smoothstep",
    animated: state.tree[index].node_id === activeId,
    style: { stroke: state.tree[index].node_id === activeId ? "#f0b90b" : "#39404c", strokeWidth: state.tree[index].node_id === activeId ? 2.2 : 1.1 },
  })), [activeId, state.tree]);
  return (
    <div className="tree-canvas">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.22 }} onNodeClick={(_, node) => onSelect(node.id)} panOnScroll zoomOnPinch zoomOnDoubleClick={false} proOptions={{ hideAttribution: true }}>
        <Background color="#2a3038" gap={24} size={1} />
      </ReactFlow>
    </div>
  );
}

function statusCopy(state: string | undefined) {
  if (state === "COMPLETED") return "终局已抵达";
  if (state === "PAUSED") return "播放已暂停";
  if (state === "DECISION_REVEAL") return "判定揭晓中";
  if (state === "PLAN_LOCKED") return "路线已冻结";
  return "正在写作";
}

function StoryReader({ state, onSelectChapter }: { state: StoryClientState; onSelectChapter: (id: string) => void }) {
  const [input, setInput] = useState("");
  const [recorded, setRecorded] = useState(false);
  const reading = state.snapshot.chapters.find((chapter) => chapter.chapter_id === state.readingChapterId) || state.snapshot.chapters.at(-1);
  const live = state.snapshot.chapters.find((chapter) => chapter.chapter_id === state.liveChapterId);
  const isLive = reading?.chapter_id === live?.chapter_id;
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!input.trim()) return;
    setRecorded(true);
    setInput("");
    window.setTimeout(() => setRecorded(false), 1800);
  };
  return (
    <section className="reader-panel">
      <div className="reader-toolbar">
        <div className="chapter-meta"><span className="eyebrow">{reading ? `LIFE ${String(reading.life_number).padStart(2, "0")}` : "WAITING"}</span><span className="dot-separator">/</span><span>{reading?.node_id || "ROOT"}</span></div>
        <div className="reader-actions"><span className={`connection ${state.connected ? "online" : "offline"}`}><span className="status-dot" />{state.connected ? "LIVE" : "SYNCING"}</span>{!isLive && live && <button className="ghost-button" onClick={() => onSelectChapter(live.chapter_id)}><Radio size={14} />回到实时</button>}</div>
      </div>
      <div className="reader-scroll">
        <AnimatePresence mode="wait">
          <motion.article key={reading?.chapter_id || "empty"} className="chapter-article" initial={{ opacity: .35, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .35 }}>
            <div className="chapter-kicker"><span>CHAPTER {reading?.chapter_index || "--"}</span><span>{reading?.generation_status === "generating" ? "· GENERATING" : "· ARCHIVED"}</span></div>
            <h1>{reading?.chapter_title || "故事正在准备"}</h1>
            <div className="chapter-location"><span>{state.tree.find((node) => node.node_id === reading?.node_id)?.time_range || ""}</span><span>{state.tree.find((node) => node.node_id === reading?.node_id)?.location || ""}</span></div>
            <div className="chapter-copy">{reading?.content ? reading.content.split(/\n\n+/).map((paragraph, index) => <p key={`${reading.chapter_id}-${index}`}>{paragraph}</p>) : <p className="muted-copy">下一段正文将在判定完成后出现。</p>}</div>
            {isLive && <div className="typing-line"><span /><span /><span /></div>}
          </motion.article>
        </AnimatePresence>
        {state.snapshot.chapters.length > 1 && <div className="history-strip"><div className="history-heading"><span>已完成章节</span><span>{state.snapshot.chapters.length}</span></div><div className="history-list">{state.snapshot.chapters.map((chapter) => <button key={chapter.chapter_id} className={`history-item ${chapter.chapter_id === reading?.chapter_id ? "selected" : ""}`} onClick={() => onSelectChapter(chapter.chapter_id)}><span>L{chapter.life_number} · {chapter.node_id}</span><strong>{chapter.chapter_title}</strong></button>)}</div></div>}
      </div>
      <form className="audience-input" onSubmit={submit}><div className="input-prefix"><Sparkles size={14} /><span>写给命运</span></div><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="留下一句旁白" aria-label="留下一句旁白" /><button type="submit" aria-label="记录旁白" title="记录旁白"><Send size={16} /></button>{recorded && <span className="recorded">已记录</span>}</form>
    </section>
  );
}

function useStoryState() {
  const [state, dispatch] = useReducer((current: StoryClientState | null, action: { type: "load"; snapshot: StoryClientState } | { type: "event"; event: StoryEvent } | { type: "connected"; value: boolean } | { type: "reading"; id: string }) => {
    if (!current) return action.type === "load" ? action.snapshot : current;
    if (action.type === "event") return applyEvent(current, action.event);
    if (action.type === "connected") return setConnected(current, action.value);
    if (action.type === "reading") return { ...current, readingChapterId: action.id };
    return action.snapshot;
  }, null);
  const [loadError, setLoadError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchSnapshot(), fetchTree()]).then(([snapshot, tree]) => {
      if (!cancelled) dispatch({ type: "load", snapshot: createInitialState(snapshot, tree.nodes) });
    }).catch((error: unknown) => {
      if (!cancelled) {
        setLoadError(error instanceof Error ? error.message : "API offline");
        dispatch({ type: "load", snapshot: createInitialState(fallbackSnapshot, fallbackTree) });
      }
    });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    if (!state) return;
    const source = new EventSource(eventStreamUrl(state.liveSequence));
    const eventNames = ["text_delta", "chapter_started", "chapter_completed", "decision_reveal", "death", "rebirth", "tree_update", "playback_paused", "story_completed"];
    const onMessage = (message: MessageEvent<string>) => {
      const event = parseEventMessage(message);
      if (event) dispatch({ type: "event", event });
    };
    eventNames.forEach((eventName) => source.addEventListener(eventName, onMessage));
    source.onopen = () => dispatch({ type: "connected", value: true });
    source.onerror = () => dispatch({ type: "connected", value: false });
    return () => { eventNames.forEach((eventName) => source.removeEventListener(eventName, onMessage)); source.close(); };
  // EventSource carries Last-Event-ID on reconnect. Keeping one connection
  // avoids resetting the stream after every text delta.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state !== null]);
  return { state, loadError, setReading: (id: string) => dispatch({ type: "reading", id }) };
}

export function StoryShell() {
  const { state, loadError, setReading } = useStoryState();
  const [treeOpen, setTreeOpen] = useState(false);
  const onSelect = useCallback((id: string) => {
    const chapter = state?.snapshot.chapters.find((item) => item.node_id === id);
    if (chapter) setReading(chapter.chapter_id);
    setTreeOpen(false);
  }, [setReading, state?.snapshot.chapters]);
  if (!state) return <main className="loading-screen"><div className="loading-mark"><Activity size={18} /><span>INITIALIZING STORY ENGINE</span></div><div className="loading-line" /></main>;
  const currentNode = state.tree.find((node) => node.node_id === state.snapshot.playback?.current_node_id);
  return (
    <main className="app-shell">
      <header className="topbar"><div className="brand-lockup"><div className="brand-mark">CZ</div><div><div className="brand-title">我的模拟首富路</div><div className="brand-subtitle">{state.snapshot.plan?.ticker || "CZ LIFE"} / PUBLIC TIMELINE</div></div></div><div className="topbar-center"><span className="signal-pill"><span className="status-dot" />{statusCopy(state.snapshot.playback?.state)}</span><span className="node-readout">{currentNode?.node_id || "ROOT"} · {currentNode?.title || "等待路线"}</span></div><div className="topbar-right"><span className="sequence">SEQ {String(state.liveSequence).padStart(5, "0")}</span><button className="icon-button mobile-tree-button" onClick={() => setTreeOpen((value) => !value)} title="打开命运树" aria-label="打开命运树"><GitBranch size={18} /></button></div></header>
      {loadError && <div className="offline-banner"><WifiOff size={14} />本地预览模式 · 等待后端连接</div>}
      <div className={`workspace ${treeOpen ? "tree-open" : ""}`}><aside className="tree-panel"><div className="panel-heading"><div><span className="eyebrow">THE FATE TREE</span><h2>命运树</h2></div><span className="node-count">{state.tree.length} NODES</span></div><div className="tree-status"><span><span className="legend-dot live" />当前路径</span><span><span className="legend-dot branch" />已发生分支</span></div><StoryTree state={state} onSelect={onSelect} /><div className="tree-footer"><span><GitBranch size={13} />完整主干已加载</span><span><ArrowUpRight size={13} />滚动探索</span></div></aside><StoryReader state={state} onSelectChapter={setReading} /></div>
      <footer className="statusbar"><span><TerminalSquare size={13} />ROUTE v{state.snapshot.plan?.version || "--"}</span><span><BookOpenText size={13} />{state.snapshot.chapters.length} CHAPTERS COMMITTED</span><span className={state.connected ? "status-live" : ""}>{state.connected ? <Wifi size={13} /> : <WifiOff size={13} />}{state.connected ? "STREAM CONNECTED" : "RECONNECTING"}</span></footer>
    </main>
  );
}
