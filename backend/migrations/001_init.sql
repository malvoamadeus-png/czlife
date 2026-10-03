CREATE TABLE IF NOT EXISTS story_plans (
    plan_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    title TEXT NOT NULL,
    ticker TEXT NOT NULL,
    status TEXT NOT NULL,
    seed BIGINT NOT NULL,
    rules_version TEXT NOT NULL,
    plan_hash TEXT,
    mainline_node_ids JSONB NOT NULL,
    max_lives INTEGER NOT NULL,
    ending JSONB NOT NULL,
    routes JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_at TIMESTAMPTZ,
    PRIMARY KEY (plan_id, version)
);

CREATE TABLE IF NOT EXISTS story_nodes (
    plan_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    node_order INTEGER NOT NULL,
    title TEXT NOT NULL,
    time_range TEXT NOT NULL,
    location TEXT NOT NULL,
    research_summary TEXT NOT NULL,
    source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    visible_context TEXT NOT NULL DEFAULT '',
    chapter_guidance TEXT NOT NULL DEFAULT '',
    evidence_level TEXT NOT NULL DEFAULT 'primary-official',
    PRIMARY KEY (plan_id, plan_version, node_id),
    FOREIGN KEY (plan_id, plan_version) REFERENCES story_plans(plan_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS decision_rules (
    plan_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    rule_id TEXT NOT NULL,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    success_threshold INTEGER NOT NULL,
    memory_effect INTEGER NOT NULL DEFAULT 0,
    fallback_rule TEXT NOT NULL DEFAULT 'death',
    PRIMARY KEY (plan_id, plan_version, rule_id),
    FOREIGN KEY (plan_id, plan_version) REFERENCES story_plans(plan_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS life_routes (
    plan_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    life_number INTEGER NOT NULL,
    route_status TEXT NOT NULL,
    failure_node_id TEXT,
    death_reason TEXT,
    gained_memory JSONB,
    inherited_memories JSONB NOT NULL DEFAULT '[]'::jsonb,
    decision_results JSONB NOT NULL DEFAULT '[]'::jsonb,
    PRIMARY KEY (plan_id, plan_version, life_number),
    FOREIGN KEY (plan_id, plan_version) REFERENCES story_plans(plan_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS decision_results (
    decision_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    life_number INTEGER NOT NULL,
    from_node_id TEXT NOT NULL,
    to_node_id TEXT NOT NULL,
    input_snapshot JSONB NOT NULL,
    rules_version TEXT NOT NULL,
    roll_value INTEGER NOT NULL,
    threshold INTEGER NOT NULL,
    result TEXT NOT NULL,
    UNIQUE(plan_id, plan_version, life_number, from_node_id),
    FOREIGN KEY (plan_id, plan_version) REFERENCES story_plans(plan_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS failure_routes (
    failure_route_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    planned_beats JSONB NOT NULL DEFAULT '[]'::jsonb,
    death_reason TEXT NOT NULL,
    chapter_count_estimate INTEGER NOT NULL DEFAULT 1,
    generation_status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS chapters (
    chapter_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    life_number INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    chapter_index INTEGER NOT NULL,
    chapter_title TEXT NOT NULL,
    generation_status TEXT NOT NULL DEFAULT 'pending',
    content TEXT NOT NULL DEFAULT '',
    committed_offset INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    UNIQUE(plan_id, plan_version, life_number, node_id, chapter_index),
    FOREIGN KEY (plan_id, plan_version) REFERENCES story_plans(plan_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stream_events (
    event_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    sequence BIGINT GENERATED ALWAYS AS IDENTITY,
    chapter_id TEXT,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(plan_id, plan_version, sequence)
);

CREATE INDEX IF NOT EXISTS stream_events_cursor_idx
    ON stream_events(plan_id, plan_version, sequence);
CREATE INDEX IF NOT EXISTS chapters_public_idx
    ON chapters(plan_id, plan_version, life_number, chapter_index);

CREATE TABLE IF NOT EXISTS playback_state (
    plan_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    state TEXT NOT NULL,
    current_route_index INTEGER NOT NULL DEFAULT 0,
    current_chapter_id TEXT,
    current_node_id TEXT,
    current_life_number INTEGER NOT NULL DEFAULT 1,
    latest_sequence BIGINT NOT NULL DEFAULT 0,
    next_run_at TIMESTAMPTZ,
    last_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(plan_id, plan_version),
    FOREIGN KEY (plan_id, plan_version) REFERENCES story_plans(plan_id, version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS operator_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

