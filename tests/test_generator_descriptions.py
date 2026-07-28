"""Unit tests for CK_server/generator/descriptions.py (PLAN-backend-module-split.md, commit 7).

Two jobs.

**Behaviour.** These functions shape every row the three review tables show, and until
commit 7 they lived inside a router module, so nothing could reach them without a
TestClient and none of them had a direct test. The extraction is only worth doing if the
result is actually exercised, so this pins the behaviour the UI depends on — full,
untruncated bodies, the soft caps, and the fallback chains that decide what a row says
when its source fields are empty.

**Single source.** The commit retired two duplicated definitions into `db`
(`GENERIC_TOKENS`, `split_atp_title_description`). A duplicate that gets deleted and then
quietly grows back is the failure mode this whole plan is about — the comment above
`db._relevance_score` already claimed "no private copy here" while a byte-identical copy
of the stoplist sat in wizard.py — so the single-definition property is asserted, not
assumed.

Pure: no TestClient, no LLM, no network. `db` is imported but only read for its constants
(the one function that queries, `enrich_zephyr_rows`, is driven here with rows whose keys
are already in the supplied `data`, so it never reaches SQLite).
"""
import ast
import pathlib

import pytest

_SERVER = pathlib.Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"


@pytest.fixture(scope="module")
def d():
    import generator.descriptions as descriptions
    return descriptions


# --- tokenizers --------------------------------------------------------------

def test_normalize_strips_the_leading_group_number(d):
    """Case titles arrive as "(163) QoS - Physical Queue"; the (163) is not a feature."""
    assert d.normalize_zephyr_text("(163) QoS - Physical Queue") == "qos   physical queue"


@pytest.mark.parametrize("raw,expected", [
    ("port_status/speed-duplex", "port status speed duplex"),
    ("", ""),
    (None, ""),
])
def test_normalize_separators_and_empties(d, raw, expected):
    assert d.normalize_zephyr_text(raw) == expected


def test_tokens_drop_words_under_three_characters(d):
    """Two-letter words are noise in an FTS query; the regex floor is 2 chars, the
    explicit length check is what actually enforces 3."""
    assert d.zephyr_tokens("an ip vlan port") == ["vlan", "port"]


def test_tokens_cluster_the_mdi_variants(d):
    """MDI / MDIX / MDI-MDIX name one physical property; ranking must see them as one.

    Both spellings are emitted for either input, which is the only reason a case titled
    "MDIX" can match a corpus row that says "MDI".
    """
    assert set(d.zephyr_tokens("mdi")) == {"mdi", "mdix"}
    assert set(d.zephyr_tokens("auto-mdix crossover")) == {"auto", "mdi", "mdix", "crossover"}


def test_tokens_keep_the_plus_in_bgp4_style_names(d):
    """[a-z0-9][a-z0-9+]+ exists so BGP4+ survives as one token rather than becoming bgp4."""
    assert "bgp4+" in d.zephyr_tokens("BGP4+ routemaps")


# --- TestLink descriptions ---------------------------------------------------

def test_testlink_description_keeps_every_step_in_full(d):
    """No mid-sentence truncation: this is the body a reviewer reads to make the call."""
    item = {"steps": [
        {"action": "Set speed to 1000", "expected": "Link comes up at 1000"},
        {"action": "Check duplex"},
        {"expected": "current duplex full"},
    ]}
    out = d.build_testlink_description(item)
    assert out == ("Step: Set speed to 1000\nExpected: Link comes up at 1000\n\n"
                   "Step: Check duplex\n\n"
                   "Expected: current duplex full")


def test_testlink_description_soft_caps_at_thirty_steps(d):
    item = {"steps": [{"action": f"step {i}"} for i in range(50)]}
    assert len(d.build_testlink_description(item).split("\n\n")) == 30


def test_testlink_description_falls_back_snippet_then_title(d):
    """Order matters — a snippet is real source text, the title is a last resort."""
    assert d.build_testlink_description({"snippet": "  a snippet  "}, title="T") == "a snippet"
    assert d.build_testlink_description({}, title="  T  ") == "T"
    assert d.build_testlink_description({"title": "from item"}) == "from item"
    assert d.build_testlink_description(None) == ""


def test_testlink_description_ignores_wholly_empty_steps(d):
    """A step with neither action nor expected must not emit a blank paragraph."""
    item = {"steps": [{"action": "", "expected": ""}], "snippet": "fallback"}
    assert d.build_testlink_description(item) == "fallback"


# --- Zephyr case descriptions ------------------------------------------------

def test_zephyr_description_assembles_every_section(d):
    slim = {"status": "Approved", "has_objective": True, "num_steps": 2,
            "labels": ["port", "speed"]}
    full = {"objective": "Verify speed", "precondition": "Link up",
            "steps": [{"description": "set speed"}, {"description": "check"}]}
    out = d.build_zephyr_case_description(slim, full)
    assert out.split("\n\n") == [
        "Objective: Verify speed",
        "Precondition: Link up",
        "Status: Approved | Has objective: True | Num steps: 2 | Labels: port, speed",
        "Steps:\n1. set speed\n2. check",
    ]


def test_zephyr_description_numbers_steps_from_one_and_caps_at_twenty(d):
    full = {"steps": [{"description": f"s{i}"} for i in range(30)]}
    body = d.build_zephyr_case_description({}, full).split("Steps:\n", 1)[1]
    lines = body.split("\n")
    assert lines[0] == "1. s0" and len(lines) == 20


def test_zephyr_description_falls_back_to_a_title_then_a_constant(d):
    """A row with nothing to say still needs a body — an empty cell reads as a bug."""
    assert d.build_zephyr_case_description({}, {}, title_fallback=" T ") == "T"
    assert d.build_zephyr_case_description({}, {}) == "Related Zephyr case"
    assert d.build_zephyr_case_description(None, None) == "Related Zephyr case"


def test_zephyr_description_reports_has_objective_false(d):
    """`if "has_objective" in slim` not `if slim.get(...)` — False is a real answer and
    is precisely the signal the Generator exists to act on."""
    assert "Has objective: False" in d.build_zephyr_case_description(
        {"has_objective": False}, {})


# --- row enrichment ----------------------------------------------------------

def test_enrich_prefers_zephyr_master_and_leaves_no_row_behind(d):
    data = {"zephyr_master": {"AWPTCM-T1": {"objective": "from master"}}}
    rows = [{"key": "AWPTCM-T1", "title": "T1"}, {"title": "no key at all"}]
    out = d.enrich_zephyr_rows(rows, data)
    assert out[0]["description"].startswith("Objective: from master")
    assert out[1] == {"title": "no key at all"}, "a keyless row passes through untouched"


def test_enrich_reports_none_for_slim_fields_the_row_never_carried(d):
    """Documenting a wart, not endorsing it.

    enrich_zephyr_rows always builds its fallback slim dict with `has_objective` and
    `num_steps` keys, present-but-None when the row lacks them, and
    build_zephyr_case_description tests membership (`"has_objective" in slim_meta`)
    rather than truthiness — so such a row renders a literal "Has objective: None |
    Num steps: None" meta line. Real db.search_zephyr rows carry both fields, so this
    is only reachable for hand-built or partial rows. Left as-is: commit 7 is a pure
    move, and changing it would be a UI behaviour change smuggled into a refactor.
    """
    out = d.enrich_zephyr_rows([{"key": "K"}], {"zephyr_master": {"K": {"objective": "o"}}})
    assert out[0]["description"] == "Objective: o\n\nHas objective: None | Num steps: None"


def test_enrich_backfills_title_and_folder_but_never_overwrites_them(d):
    data = {"zephyr_master": {"K": {"title": "master title", "folder": "Port/Auto"}}}
    out = d.enrich_zephyr_rows([{"id": "K"}, {"id": "K", "title": "mine", "folder": "Mine"}], data)
    assert (out[0]["title"], out[0]["folder"]) == ("master title", "Port/Auto")
    assert (out[1]["title"], out[1]["folder"]) == ("mine", "Mine")


def test_enrich_rewrites_a_description_that_is_only_the_title(d):
    """search_zephyr sets description=title when it has nothing better; that is the
    case this function exists to fix, so it must not be mistaken for 'already enriched'."""
    data = {"zephyr_master": {"K": {"objective": "real body"}}}
    out = d.enrich_zephyr_rows([{"key": "K", "title": "K", "description": "K"}], data)
    assert out[0]["description"].startswith("Objective: real body")


def test_enrich_does_not_query_the_db_when_master_already_has_the_case(d, monkeypatch):
    """The batch lookup is a SQLite round-trip; every already-known key must skip it."""
    calls = []
    monkeypatch.setattr(d.db, "get_zephyr_cases_batch",
                        lambda keys: calls.append(list(keys)) or {})
    data = {"zephyr_master": {"K": {"objective": "o"}}}
    d.enrich_zephyr_rows([{"key": "K"}], data)
    assert calls == [], "no key needed fetching"
    d.enrich_zephyr_rows([{"key": "MISSING"}], data)
    assert calls == [["MISSING"]]


# --- ATP query + retrieval ---------------------------------------------------

def _session(**kw):
    from models import Selection, WizardSession
    sess = WizardSession(key=kw.pop("key", "AWPTCM-T33233"))
    sess.primary = kw.pop("primary", None)
    for step, sels in (("step1", kw.pop("step1", [])), ("step2", kw.pop("step2", []))):
        getattr(sess, step).selections = [Selection(**s) for s in sels]
    return sess


def test_atp_query_strips_generics_and_keeps_the_feature_words(d):
    sess = _session(primary={"w": "Auto negotiation check", "m": "AWP-123"},
                    step1=[{"id_or_key": "AWP-1", "title": "duplex mismatch",
                            "justification": "covers renegotiation"}])
    q = d.build_atp_query(sess, case_title="Port - Auto Negotiation")
    toks = q.split()
    assert "negotiation" in toks and "duplex" in toks and "mismatch" in toks
    assert not (set(toks) & d.db.GENERIC_TOKENS), f"generic token survived: {toks}"


def test_atp_query_caps_the_token_budget(d):
    sess = _session(step1=[{"id_or_key": "x", "title": " ".join(f"tok{i}" for i in range(60))}])
    assert len(d.build_atp_query(sess).split()) == 24


def test_atp_query_falls_back_to_raw_when_everything_was_generic(d):
    """An empty FTS query returns nothing at all, so a degraded query beats no query."""
    sess = _session(key="", primary={"w": "port switch interface", "m": ""})
    q = d.build_atp_query(sess, case_title="test config")
    assert "port" in q and "switch" in q, "the raw text must survive as a fallback"


def test_hybrid_is_the_default_but_keyword_is_honoured(d, monkeypatch):
    monkeypatch.setattr(d.db, "HAS_VEC", True)
    assert d.hybrid_on("") and d.hybrid_on("hybrid") and d.hybrid_on("semantic")
    assert not d.hybrid_on("keyword") and not d.hybrid_on("KEYWORD")


def test_hybrid_degrades_to_keyword_without_vectors(d, monkeypatch):
    """No sqlite-vec means no embeddings table; asking for hybrid anyway would query
    a KNN index that cannot answer."""
    monkeypatch.setattr(d.db, "HAS_VEC", False)
    assert not d.hybrid_on("") and not d.hybrid_on("hybrid")


def test_get_atp_candidates_routes_to_the_mode_it_was_asked_for(d, monkeypatch):
    seen = []
    monkeypatch.setattr(d.db, "HAS_VEC", True)
    monkeypatch.setattr(d.db, "search_atp", lambda q, **k: seen.append(("kw", q)) or [])
    monkeypatch.setattr(d.db, "search_atp_hybrid", lambda q, **k: seen.append(("hy", q)) or [])
    d.get_atp_candidates("q1", {}, mode="keyword")
    d.get_atp_candidates("q2", {})
    assert seen == [("kw", "q1"), ("hy", "q2")]


# --- single source of truth --------------------------------------------------

def _module_defines(rel, name):
    tree = ast.parse((_SERVER / rel).read_text(encoding="utf-8"))
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            return True
        if isinstance(n, ast.Assign) and any(
                getattr(t, "id", None) == name for t in n.targets):
            return True
    return False


@pytest.mark.parametrize("name", ["GENERIC_TOKENS", "_ZREF_GENERIC_TOKENS"])
def test_the_generic_token_stoplist_is_defined_only_in_db(name):
    """It was byte-identical in db.py and wizard.py — two copies of the vocabulary that
    decides what every search ranks on. Whichever name it goes by, db owns the only one.
    """
    others = [rel for rel in ("routers/wizard.py", "generator/descriptions.py")
              if _module_defines(rel, name)]
    assert not others, f"{name} redefined outside db.py in {others}"
    if name == "GENERIC_TOKENS":
        assert _module_defines("db.py", name), "db.py must still define it"


@pytest.mark.parametrize("name", ["split_atp_title_description",
                                  "_split_atp_title_description"])
def test_the_atp_title_split_is_defined_only_in_db(name):
    """db.py's copy was labelled "Verbatim from wizard.py" and was in fact structurally
    identical. db.search_atp calls it, so db is where it has to live — a router-owned
    copy would make the data layer depend on the route layer to split its own rows.
    """
    others = [rel for rel in ("routers/wizard.py", "generator/descriptions.py")
              if _module_defines(rel, name)]
    assert not others, f"{name} redefined outside db.py in {others}"


# test_descriptions_never_imports_the_router_layer lived here until commit 10's rename.
# tests/test_shared_modules_decoupling.py::test_the_shared_leaves_never_import_a_router is
# the same assertion parametrized over EVERY extracted leaf, so this narrower copy is gone
# rather than repaired — it only ever covered one of the six.


def test_the_extracted_helpers_left_the_router():
    """The point of the commit: these names are gone from wizard.py, not aliased there."""
    moved = ["_normalize_zephyr_text", "_zephyr_tokens", "_build_testlink_description",
             "_build_zephyr_case_description", "_enrich_zephyr_rows", "_build_atp_query",
             "_get_atp_candidates", "_hybrid_on", "_get_full_zephyr_cases_batch"]
    back = [n for n in moved if _module_defines("routers/wizard.py", n)]
    assert not back, f"routers/wizard.py still defines {back}"
