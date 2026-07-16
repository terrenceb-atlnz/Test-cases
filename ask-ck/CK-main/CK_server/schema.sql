-- Ask-CK SQLite data layer — base tables + FTS5 (Commit A).
--
-- See ask-ck/ck-facelift/PLAN-db-migration.md. The DB (ask-ck/var/ck.db) is a
-- DERIVED, REBUILDABLE cache: the XML export + extractor JSON outputs under
-- objective-drafting/data and pytest-create/data remain the source of truth.
-- Rebuild with `python3 tool/build_db.py --fresh`.
--
-- Normalization policy: normalize what is searched/filtered; keep rarely-
-- individually-queried nested data as JSON1 text columns (steps, labels,
-- helpers, test_cases, log_analysis). A flattened *_text column feeds FTS —
-- no child step tables (nothing queries a single step).
--
-- Vector (sqlite-vec) tables + embeddings_meta are deliberately NOT here; they
-- are added in Stage D so the server never fails startup when the extension is
-- absent. This file is Commit A: keyword (FTS5/BM25) retrieval only.

PRAGMA journal_mode=WAL;

-- ─────────────────────────────────────────────────────────────────────────────
-- Meta
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meta (
  k TEXT PRIMARY KEY,
  v TEXT
);  -- schema_version, source sha1/mtimes, ingest counts, built_at

-- ─────────────────────────────────────────────────────────────────────────────
-- Zephyr cases  (45,427 xml + 410 api-target merged; api wins on key conflict)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zephyr_cases (
  id            INTEGER PRIMARY KEY,
  key           TEXT NOT NULL UNIQUE,
  src           TEXT NOT NULL,                         -- 'api' | 'xml'
  is_target     INTEGER NOT NULL DEFAULT 0,            -- 1 = the 410 zephyr_master cases
  title         TEXT NOT NULL DEFAULT '',
  folder        TEXT NOT NULL DEFAULT '',
  objective     TEXT,
  precondition  TEXT,
  priority      TEXT,
  status        TEXT,
  labels        TEXT,                                  -- JSON array
  script_type   TEXT,
  script_text   TEXT,
  steps         TEXT,                                  -- JSON array [{description,testData,expected}]
  steps_text    TEXT NOT NULL DEFAULT '',              -- flattened step text (feeds FTS)
  num_steps     INTEGER NOT NULL DEFAULT 0,
  has_objective INTEGER NOT NULL DEFAULT 0,
  content_sha1  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_zephyr_is_target ON zephyr_cases(is_target);
CREATE INDEX IF NOT EXISTS idx_zephyr_folder    ON zephyr_cases(folder);

-- ─────────────────────────────────────────────────────────────────────────────
-- TestLink cases  (21,624 historical AWP-* cases)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS testlink_cases (
  id            TEXT PRIMARY KEY,                      -- full_external_id, e.g. AWP-4357
  internal_id   TEXT,
  title         TEXT NOT NULL DEFAULT '',
  suite_top     TEXT,
  suite         TEXT,
  summary       TEXT,
  preconditions TEXT,
  importance    TEXT,
  status        TEXT,
  steps         TEXT,                                  -- JSON array [{n,action,expected}]
  steps_text    TEXT NOT NULL DEFAULT '',              -- first 20 steps flattened (matches search blob)
  content_sha1  TEXT NOT NULL
);

-- ─────────────────────────────────────────────────────────────────────────────
-- ATP tests  (10,157 enriched ATPyLib tests, keyed "suite.testSet.caseId")
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS atp_tests (
  tid           TEXT PRIMARY KEY,
  suite_id      TEXT NOT NULL,                         -- NOT NULL: past schema drift silently dropped 12 suites
  suite_name    TEXT NOT NULL,
  test_set      TEXT,
  case_id       TEXT,
  description   TEXT NOT NULL DEFAULT '',
  reference     TEXT,
  past_crs      TEXT,
  current_crs   TEXT,
  log_analysis  TEXT,                                  -- JSON (opaque)
  is_functional INTEGER NOT NULL DEFAULT 1,            -- precomputed "(not a functional test)" filter
  content_sha1  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_atp_suite ON atp_tests(suite_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- Scripts index  (830 files across testsuites_art / svt_scripts / test_scripts)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scripts (
  id             TEXT PRIMARY KEY,
  db             TEXT,                                 -- 'art' | 'svt' | 'test'
  path           TEXT NOT NULL,
  suite_dir      TEXT,
  kind           TEXT,                                 -- 'test' | 'lib' | 'tool' | ...
  sha1           TEXT NOT NULL,
  mtime          REAL,
  loc_total      INTEGER,
  parse_error    TEXT,
  title          TEXT,
  summary        TEXT,
  docstring      TEXT,
  feature_tags   TEXT,                                 -- JSON array
  covered_actions TEXT,                                -- JSON array
  imports        TEXT,                                 -- JSON
  testset        TEXT,                                 -- JSON
  test_cases     TEXT,                                 -- JSON
  helpers        TEXT,                                 -- JSON
  tags_text      TEXT NOT NULL DEFAULT '',             -- feature_tags + covered_actions flattened (feeds FTS)
  dir_text       TEXT NOT NULL DEFAULT ''              -- suite_dir flattened (feeds FTS)
);
CREATE INDEX IF NOT EXISTS idx_scripts_db ON scripts(db);

-- ─────────────────────────────────────────────────────────────────────────────
-- Generator pipeline docs (rebuildable from JSON source of truth)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
  case_key TEXT PRIMARY KEY,                           -- REFERENCES zephyr_cases(key) logically
  payload  TEXT NOT NULL                               -- whole candidates.json record as JSON
);

CREATE TABLE IF NOT EXISTS decisions (
  key         TEXT PRIMARY KEY,
  matched_id  TEXT,                                    -- record 'm'
  confidence  TEXT,                                    -- record 'c'
  rationale   TEXT,                                    -- record 'w'
  source_file TEXT NOT NULL                            -- dec_NN.json
);

CREATE TABLE IF NOT EXISTS json_docs (
  name       TEXT PRIMARY KEY,                         -- framework_surface, scripts_index_meta, ...
  payload    TEXT NOT NULL,
  updated_at TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Sessions  (Commit C imports these; table created now, populated later)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
  id         TEXT PRIMARY KEY,                         -- 'AWPTCM-Txxxx' | 'pt-…' | '_workspace_llm'
  kind       TEXT NOT NULL CHECK (kind IN ('wizard','pt','workspace')),
  case_key   TEXT,
  payload    TEXT NOT NULL,                            -- model dump MINUS llm_config
  llm_config TEXT,                                     -- separate column: never selected by log/progress queries
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_kind ON sessions(kind);

-- ═════════════════════════════════════════════════════════════════════════════
-- FTS5 external-content indexes (one copy of text; bm25() weights; snippet())
-- Rebuilt via ('rebuild') at the end of every ingest — corpora are only ever
-- written by build_db.py, so the base tables are authoritative.
-- ═════════════════════════════════════════════════════════════════════════════
CREATE VIRTUAL TABLE IF NOT EXISTS zephyr_fts USING fts5(
  key, title, folder, objective, steps_text,
  content='zephyr_cases', content_rowid='id',
  tokenize="unicode61 remove_diacritics 2 tokenchars '.+'", prefix='2 3'
);

CREATE VIRTUAL TABLE IF NOT EXISTS testlink_fts USING fts5(
  id, title, summary, steps_text,
  content='testlink_cases', content_rowid='rowid',
  tokenize="unicode61 remove_diacritics 2 tokenchars '.+'", prefix='2 3'
);

CREATE VIRTUAL TABLE IF NOT EXISTS atp_fts USING fts5(
  tid, description, suite_name,
  content='atp_tests', content_rowid='rowid',
  tokenize="unicode61 remove_diacritics 2 tokenchars '.+'", prefix='2 3'
);

CREATE VIRTUAL TABLE IF NOT EXISTS scripts_fts USING fts5(
  id, title, summary, tags_text, dir_text, docstring,
  content='scripts', content_rowid='rowid',
  tokenize="unicode61 remove_diacritics 2 tokenchars '.+'", prefix='2 3'
);

-- External-content sync triggers.
-- zephyr_cases has an explicit INTEGER PRIMARY KEY (id) used as content_rowid;
-- the other three use the implicit rowid. All keep the FTS shadow tables in
-- lockstep so incremental writes stay correct even between full ('rebuild')s.

CREATE TRIGGER IF NOT EXISTS zephyr_ai AFTER INSERT ON zephyr_cases BEGIN
  INSERT INTO zephyr_fts(rowid, key, title, folder, objective, steps_text)
  VALUES (new.id, new.key, new.title, new.folder, new.objective, new.steps_text);
END;
CREATE TRIGGER IF NOT EXISTS zephyr_ad AFTER DELETE ON zephyr_cases BEGIN
  INSERT INTO zephyr_fts(zephyr_fts, rowid, key, title, folder, objective, steps_text)
  VALUES ('delete', old.id, old.key, old.title, old.folder, old.objective, old.steps_text);
END;
CREATE TRIGGER IF NOT EXISTS zephyr_au AFTER UPDATE ON zephyr_cases BEGIN
  INSERT INTO zephyr_fts(zephyr_fts, rowid, key, title, folder, objective, steps_text)
  VALUES ('delete', old.id, old.key, old.title, old.folder, old.objective, old.steps_text);
  INSERT INTO zephyr_fts(rowid, key, title, folder, objective, steps_text)
  VALUES (new.id, new.key, new.title, new.folder, new.objective, new.steps_text);
END;

CREATE TRIGGER IF NOT EXISTS testlink_ai AFTER INSERT ON testlink_cases BEGIN
  INSERT INTO testlink_fts(rowid, id, title, summary, steps_text)
  VALUES (new.rowid, new.id, new.title, new.summary, new.steps_text);
END;
CREATE TRIGGER IF NOT EXISTS testlink_ad AFTER DELETE ON testlink_cases BEGIN
  INSERT INTO testlink_fts(testlink_fts, rowid, id, title, summary, steps_text)
  VALUES ('delete', old.rowid, old.id, old.title, old.summary, old.steps_text);
END;
CREATE TRIGGER IF NOT EXISTS testlink_au AFTER UPDATE ON testlink_cases BEGIN
  INSERT INTO testlink_fts(testlink_fts, rowid, id, title, summary, steps_text)
  VALUES ('delete', old.rowid, old.id, old.title, old.summary, old.steps_text);
  INSERT INTO testlink_fts(rowid, id, title, summary, steps_text)
  VALUES (new.rowid, new.id, new.title, new.summary, new.steps_text);
END;

CREATE TRIGGER IF NOT EXISTS atp_ai AFTER INSERT ON atp_tests BEGIN
  INSERT INTO atp_fts(rowid, tid, description, suite_name)
  VALUES (new.rowid, new.tid, new.description, new.suite_name);
END;
CREATE TRIGGER IF NOT EXISTS atp_ad AFTER DELETE ON atp_tests BEGIN
  INSERT INTO atp_fts(atp_fts, rowid, tid, description, suite_name)
  VALUES ('delete', old.rowid, old.tid, old.description, old.suite_name);
END;
CREATE TRIGGER IF NOT EXISTS atp_au AFTER UPDATE ON atp_tests BEGIN
  INSERT INTO atp_fts(atp_fts, rowid, tid, description, suite_name)
  VALUES ('delete', old.rowid, old.tid, old.description, old.suite_name);
  INSERT INTO atp_fts(rowid, tid, description, suite_name)
  VALUES (new.rowid, new.tid, new.description, new.suite_name);
END;

CREATE TRIGGER IF NOT EXISTS scripts_ai AFTER INSERT ON scripts BEGIN
  INSERT INTO scripts_fts(rowid, id, title, summary, tags_text, dir_text, docstring)
  VALUES (new.rowid, new.id, new.title, new.summary, new.tags_text, new.dir_text, new.docstring);
END;
CREATE TRIGGER IF NOT EXISTS scripts_ad AFTER DELETE ON scripts BEGIN
  INSERT INTO scripts_fts(scripts_fts, rowid, id, title, summary, tags_text, dir_text, docstring)
  VALUES ('delete', old.rowid, old.id, old.title, old.summary, old.tags_text, old.dir_text, old.docstring);
END;
CREATE TRIGGER IF NOT EXISTS scripts_au AFTER UPDATE ON scripts BEGIN
  INSERT INTO scripts_fts(scripts_fts, rowid, id, title, summary, tags_text, dir_text, docstring)
  VALUES ('delete', old.rowid, old.id, old.title, old.summary, old.tags_text, old.dir_text, old.docstring);
  INSERT INTO scripts_fts(rowid, id, title, summary, tags_text, dir_text, docstring)
  VALUES (new.rowid, new.id, new.title, new.summary, new.tags_text, new.dir_text, new.docstring);
END;
