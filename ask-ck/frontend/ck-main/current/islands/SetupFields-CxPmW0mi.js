/* Built from ask-ck/frontend/ck-main/current/svelte-src/ — do not edit; run `npm run build` there.
* source-sha256:1206112986e1464d57b15314760c388e9a3bf8ac7cadfa2db25759e6165fac97 */
import { A as delegated, B as sibling, C as set_text, D as from_html, E as comment, F as user_effect, G as user_derived, H as set, J as next, K as pop, L as child, M as get, N as untrack, P as template_effect, R as first_child, T as append, U as state, V as proxy, Y as reset, _ as clsx, a as bind_checked, c as remove_input_defaults, f as bind_select_value, g as set_class, i as bind_this, j as event, k as delegate, l as set_attribute, m as select_option, n as onMount, p as init_select, q as push, r as prop, s as bind_value, t as onDestroy, u as set_checked, v as each, x as if_block, y as index, z as only_child } from "./disclose-version-XCxqLbnz.js";
//#region src/tc/api.js
var TC_API = "/api/test-composer";
async function json(r) {
	const d = await r.json().catch(() => ({}));
	if (!r.ok) {
		const det = d.detail;
		throw new Error(typeof det === "string" ? det : det && det.error ? det.error : d.error || `HTTP ${r.status}`);
	}
	return d;
}
function httpServer(base = TC_API) {
	return async function server(path, opts = {}) {
		return json(await fetch(base + path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts)));
	};
}
/** The seat agent's session routes. Every POST is JSON (the agent refuses anything else). */
function httpAgent(base = "http://127.0.0.1:8765") {
	const post = async (path, body) => json(await fetch(base + path, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(body || {})
	}));
	return {
		base,
		health: async () => json(await fetch(base + "/health")),
		start: (body) => post("/session/start", body),
		events: async (sid, after, wait = 20) => json(await fetch(`${base}/session/${encodeURIComponent(sid)}/events?after=${after}&wait=${wait}`)),
		answer: (sid, body) => post(`/session/${encodeURIComponent(sid)}/answer`, body),
		message: (sid, text) => post(`/session/${encodeURIComponent(sid)}/message`, { text }),
		stop: (sid) => post(`/session/${encodeURIComponent(sid)}/stop`, {}),
		sessions: async () => json(await fetch(base + "/sessions"))
	};
}
/** Per-seat remembered setup answers (a convenience — confirmed every launch). */
var SETUP_KEY = "ck.tc.setup";
function loadSetup(store) {
	try {
		return JSON.parse((store || window.localStorage).getItem(SETUP_KEY) || "{}");
	} catch (_) {
		return {};
	}
}
function saveSetup(v, store) {
	try {
		(store || window.localStorage).setItem(SETUP_KEY, JSON.stringify(v));
	} catch (_) {}
}
/** "u0=1, u1=7" → {u0: 1, u1: 7}; ignores anything else. */
function parseOutlets(text) {
	const out = {};
	for (const part of String(text || "").split(/[,\s]+/)) {
		const m = part.match(/^(u\d{1,2})=(\d{1,3})$/);
		if (m) out[m[1]] = Number(m[2]);
	}
	return out;
}
function formatOutlets(o) {
	return Object.entries(o || {}).map(([k, v]) => `${k}=${v}`).join(", ");
}
/** The request body for POST /runs from the setup fields. */
function runBody(kind, setup, extra = {}) {
	const pdu = setup.pduIp ? {
		ip: setup.pduIp.trim(),
		outlets: parseOutlets(setup.outlets)
	} : null;
	return Object.assign({
		kind,
		testbox: (setup.testbox || "").trim(),
		consoles: (setup.consoles || "").trim(),
		pdu,
		constraints: (setup.constraints || "").trim(),
		options: { email: (setup.email || "").trim() || null }
	}, extra);
}
/** Run Scripts' share link (PLAN-run-scripts §3): the scripts in run order and the bench settings,
*  never the email (R-D4) — whoever opens it gets the mail. Parsed by test-composer.js deepLink. */
function scriptsLink(href, { source, scripts, setup, start }) {
	const u = new URL(href);
	u.search = "";
	u.hash = "";
	const put = (k, v) => {
		const t = String(v || "").trim();
		if (t) u.searchParams.set(k, t);
	};
	put("panel", "run-scripts");
	put("source", source);
	put("scripts", (scripts || []).join(","));
	put("testbox", setup.testbox);
	put("consoles", setup.consoles);
	put("pdu", setup.pduIp);
	put("outlets", setup.outlets);
	put("constraints", setup.constraints);
	put("start", start);
	return u.toString();
}
var VERDICT_ORDER = [
	"PASS",
	"FAIL",
	"PARTIAL",
	"UNSUPPORTED",
	"ERROR",
	"BLOCKED",
	"NOT TESTED",
	"SKIP",
	"PENDING"
];
/** The results table grouped by test cycle, in first-seen order; cases without a cycle last. */
function byCycle(table) {
	const groups = /* @__PURE__ */ new Map();
	for (const row of table || []) {
		const k = row.cycle || "";
		if (!groups.has(k)) groups.set(k, []);
		groups.get(k).push(row);
	}
	return [...groups.keys()].sort((a, b) => (a === "") - (b === "")).map((k) => ({
		cycle: k || null,
		rows: groups.get(k)
	}));
}
function effectiveVerdict(row) {
	return row.regrade && row.regrade.verdict || row.verdict;
}
function verdictCounts(table) {
	const c = {};
	for (const r of table || []) {
		const v = effectiveVerdict(r);
		c[v] = (c[v] || 0) + 1;
	}
	return VERDICT_ORDER.filter((v) => c[v]).map((v) => ({
		verdict: v,
		n: c[v]
	})).concat(Object.keys(c).filter((v) => !VERDICT_ORDER.includes(v)).map((v) => ({
		verdict: v,
		n: c[v]
	})));
}
function fmtDuration(ms) {
	if (ms == null || ms < 0) return "—";
	const s = Math.round(ms / 1e3);
	const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
	return h ? `${h}h ${String(m).padStart(2, "0")}m` : m ? `${m}m ${String(x).padStart(2, "0")}s` : `${x}s`;
}
function fmtTokens(n) {
	if (n == null) return "—";
	return n >= 1e6 ? `${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}k` : String(n);
}
/** Tokens in a result event's model_usage (all models, subagents included). */
function tokensOf(modelUsage) {
	let t = 0;
	for (const u of Object.values(modelUsage || {})) t += [
		"inputTokens",
		"outputTokens",
		"cacheReadInputTokens",
		"cacheCreationInputTokens"
	].reduce((a, k) => a + (u[k] || 0), 0);
	return t || null;
}
//#endregion
//#region src/tc/AgentWindow.svelte
var root$4 = from_html(`<button type="button" class="btn btn-secondary btn-compact-small tc-stop">Stop</button>`);
var root_1$3 = from_html(`<div class="tc-problem"> </div>`);
var root_2$3 = from_html(`<span class="tc-reply-tag">reply</span>`);
var root_3$3 = from_html(`<div><!> </div>`);
var root_4$2 = from_html(`<pre class="tc-pre"> </pre>`);
var root_5$2 = from_html(`<div><button type="button" class="tc-tool-row"><span> </span> <b> </b> <span class="tc-small"> </span> <span> </span></button> <!></div>`);
var root_6$2 = from_html(`<div class="tc-ev tc-task"> </div>`);
var root_7$2 = from_html(`<div class="tc-attn-why"> </div>`);
var root_8$2 = from_html(`<div> <!></div>`);
var root_9$1 = from_html(`<div> </div>`);
var root_10$1 = from_html(`<button type="button" class="btn btn-secondary btn-compact-small"> </button>`);
var root_11$1 = from_html(`<div class="tc-opts"><!> <input class="form-input tc-other" placeholder="Other…"/> <button type="button" class="btn btn-primary btn-compact-small">Send</button></div>`);
var root_12$1 = from_html(`<div class="tc-small"> </div>`);
var root_13$1 = from_html(`<div class="tc-q"> </div> <!>`, 1);
var root_14$1 = from_html(`<div class="tc-ev tc-card"><div class="tc-card-head">The session asks</div> <!></div>`);
var root_15 = from_html(`<button type="button" class="btn btn-primary btn-compact-small">Allow</button> <button type="button" class="btn btn-secondary btn-compact-small">Deny</button>`, 1);
var root_16 = from_html(`<div class="tc-ev tc-card"><div class="tc-card-head"> </div> <pre class="tc-pre"> </pre> <!></div>`);
var root_17 = from_html(`<div class="tc-ev tc-turn"> </div>`);
var root_18 = from_html(`<div class="tc-ev tc-user"> </div>`);
var root_19 = from_html(`<div class="tc-ev tc-statechg"> </div>`);
var root_20 = from_html(`<div class="tc-empty">Waiting for the session's first event…</div>`);
var root_21 = from_html(`<div class="tc-say"><input class="form-input" placeholder="Message the session (e.g. “don’t touch u3”)"/> <button type="button" class="btn btn-secondary">Send</button></div>`);
var root_22 = from_html(`<div><div class="tc-window-head"><span> </span> <span class="tc-small"> </span> <span class="tc-spacer"></span> <span class="tc-small" title="wall clock since the session's first event"> </span> <span class="tc-small" title="all models, subagents included"> </span> <span class="tc-small"> </span> <label class="tc-small"><input type="checkbox"/> Follow</label> <label class="tc-small" title="Also show the tester's (subagents') reasoning"><input type="checkbox" class="tc-verbose"/> Verbose</label> <!></div> <!> <div class="tc-stream"><!> <!></div> <!></div>`);
function AgentWindow($$anchor, $$props) {
	push($$props, true);
	let sessionId = prop($$props, "sessionId", 3, null), onstate = prop($$props, "onstate", 3, () => {}), compact = prop($$props, "compact", 3, false);
	let events = state(proxy([]));
	const liveAtStart = untrack(() => !!sessionId());
	let sid = untrack(() => sessionId());
	let state$1 = state(proxy(liveAtStart ? "starting" : "viewing"));
	let error = state(null);
	let mode = state(proxy(liveAtStart ? "live" : "server"));
	let follow = state(true);
	let open = state(proxy({}));
	let draft = state("");
	let verbose = state(proxy(readVerbose()));
	let other = proxy({});
	let answered = state(proxy({}));
	let stopped = false;
	let box;
	const replies = user_derived(() => {
		const out = /* @__PURE__ */ new Set();
		let waiting = false;
		for (const e of get(events)) if (e.kind === "user_message") waiting = true;
		else if (waiting && !e.parent && (e.kind === "text" || e.kind === "thinking") && e.text) {
			out.add(e.seq);
			waiting = false;
		}
		return out;
	});
	const taskStarts = user_derived(() => new Map(get(events).filter((e) => e.kind === "task" && e.subtype === "task_started").map((e) => [e.task_id, e])));
	function taskLabel(e) {
		if (e.subtype === "task_updated" || e.subtype === "task_progress") return null;
		const s = (e.subtype === "task_started" ? e : get(taskStarts).get(e.task_id)) || e;
		if (!s.subagent_type && !s.background) return null;
		const what = s.subagent_type ? `subagent ${s.subagent_type}` : "background task";
		const how = e.subtype === "task_started" ? "started" : e.status || e.subtype.replace("task_", "");
		const toks = e.usage && e.usage.total_tokens ? ` · ${fmtTokens(e.usage.total_tokens)} tokens` : "";
		return `${what} ${s.description || ""} — ${how}${toks}`;
	}
	const results = user_derived(() => new Map(get(events).filter((e) => e.kind === "tool_result").map((e) => [e.id, e])));
	const lastResult = user_derived(() => [...get(events)].reverse().find((e) => e.kind === "result"));
	const updatesCost = user_derived(() => get(events).reduce((a, e) => a + (e.kind === "update" && typeof e.cost_usd === "number" ? e.cost_usd : 0), 0));
	const cost = user_derived(() => get(lastResult) || get(updatesCost) ? (get(lastResult) && get(lastResult).total_cost_usd || 0) + get(updatesCost) : null);
	const tokens = user_derived(() => get(lastResult) ? tokensOf(get(lastResult).model_usage) : null);
	const elapsed = user_derived(() => get(events).length ? Math.round((get(events)[get(events).length - 1].t || 0) * 1e3) : null);
	const pendingIds = user_derived(() => new Set(get(events).filter((e) => e.kind === "answered").map((e) => e.request_id)));
	const live = user_derived(() => ["starting", "running"].includes(get(state$1)) && get(mode) === "live");
	function readVerbose() {
		try {
			return localStorage.getItem("ckAgentVerbose") === "1";
		} catch {
			return false;
		}
	}
	function setVerbose(v) {
		set(verbose, v, true);
		try {
			localStorage.setItem("ckAgentVerbose", v ? "1" : "0");
		} catch {}
	}
	function scroll() {
		if (get(follow) && box) queueMicrotask(() => {
			box.scrollTop = box.scrollHeight;
		});
	}
	let unsent = [];
	async function relay(evs) {
		unsent = unsent.concat(evs);
		if (!unsent.length) return;
		try {
			await $$props.server(`/runs/${encodeURIComponent($$props.runId)}/events`, {
				method: "POST",
				body: JSON.stringify({
					events: unsent,
					session_id: sid
				})
			});
			unsent = [];
			if (get(error) && get(error).startsWith("Could not save")) set(error, null);
		} catch (e) {
			set(error, `Could not save ${unsent.length} event(s) to the run record (will retry): ${e.message}`);
		}
	}
	function take(evs) {
		if (!evs.length) return;
		const have = new Set(get(events).map((e) => e.seq));
		const fresh = evs.filter((e) => !have.has(e.seq));
		if (!fresh.length) return;
		set(events, [...get(events), ...fresh].sort((a, b) => a.seq - b.seq), true);
		for (const e of fresh) if (e.kind === "state") {
			set(state$1, e.state, true);
			onstate()(e.state);
		}
		scroll();
	}
	async function pollAgent() {
		let after = 0;
		while (!stopped && get(mode) === "live") try {
			const d = await $$props.agent.events(sid, after, 20);
			take(d.events);
			await relay(d.events);
			after = d.next;
			if (d.state && d.state !== get(state$1)) {
				set(state$1, d.state, true);
				onstate()(d.state);
			}
			if ([
				"done",
				"error",
				"stopped"
			].includes(d.state) && !d.events.length) break;
		} catch (e) {
			set(error, `Lost the seat agent (${e.message}) — showing the server's copy.`);
			set(mode, "server");
		}
		if (get(mode) === "server" && !stopped) pollServer();
	}
	async function pollServer() {
		let after = get(events).length ? get(events)[get(events).length - 1].seq : -1;
		while (!stopped && get(mode) === "server") {
			try {
				const d = await $$props.server(`/runs/${encodeURIComponent($$props.runId)}/events?after=${after}`);
				take(d.events);
				if (d.events.length) after = d.events[d.events.length - 1].seq;
				if ([
					"done",
					"error",
					"stopped"
				].includes(get(state$1))) break;
			} catch (e) {
				set(error, e.message, true);
			}
			await new Promise((r) => setTimeout(r, 3e3));
		}
	}
	async function answerQuestion(ev, q, label) {
		const answers = {};
		answers[q.question] = label;
		try {
			await $$props.agent.answer(sid, {
				request_id: ev.request_id,
				answers
			});
			set(answered, {
				...get(answered),
				[ev.request_id]: true
			}, true);
		} catch (e) {
			set(error, e.message, true);
		}
	}
	async function approve(ev, allow) {
		try {
			await $$props.agent.answer(sid, {
				request_id: ev.request_id,
				allow,
				message: allow ? "" : "Denied in Ask-CK."
			});
			set(answered, {
				...get(answered),
				[ev.request_id]: true
			}, true);
		} catch (e) {
			set(error, e.message, true);
		}
	}
	async function send() {
		const text = get(draft).trim();
		if (!text) return;
		try {
			await $$props.agent.message(sid, text);
			set(draft, "");
		} catch (e) {
			set(error, e.message, true);
		}
	}
	async function stop() {
		try {
			await $$props.agent.stop(sid);
		} catch (e) {
			set(error, e.message, true);
		}
	}
	function markerClass(line) {
		if (line.startsWith("NOTIFY")) return "tc-m-notify";
		if (line.startsWith("ASKCK-DONE")) return "tc-m-done";
		const v = (line.split(/\s+/)[2] || "").toUpperCase();
		return v === "PASS" ? "tc-m-pass" : ["FAIL", "ERROR"].includes(v) ? "tc-m-fail" : "tc-m-other";
	}
	async function attach() {
		try {
			const mine = ((await $$props.agent.sessions()).sessions || []).filter((x) => x.run_id === $$props.runId).sort((a, b) => (b.started || 0) - (a.started || 0))[0];
			if (mine && !stopped) {
				sid = mine.session_id;
				set(mode, "live");
				set(state$1, mine.state, true);
				pollAgent();
				return;
			}
		} catch (_) {}
		if (!stopped) pollServer();
	}
	onMount(() => {
		if (get(mode) === "live") pollAgent();
		else attach();
	});
	onDestroy(() => {
		stopped = true;
	});
	var div = root_22();
	let classes;
	var div_1 = child(div);
	var span = child(div_1);
	var text_1 = only_child(span, true);
	var span_1 = sibling(span, 2);
	var text_2 = only_child(span_1, true);
	var span_2 = sibling(span_1, 4);
	var text_3 = only_child(span_2);
	var span_3 = sibling(span_2, 2);
	var text_4 = only_child(span_3);
	var span_4 = sibling(span_3, 2);
	var text_5 = only_child(span_4, true);
	var label_1 = sibling(span_4, 2);
	var input = child(label_1);
	remove_input_defaults(input);
	next();
	reset(label_1);
	var label_2 = sibling(label_1, 2);
	var input_1 = child(label_2);
	remove_input_defaults(input_1);
	next();
	reset(label_2);
	var node = sibling(label_2, 2);
	var consequent = ($$anchor) => {
		var button = root$4();
		delegated("click", button, stop);
		append($$anchor, button);
	};
	if_block(node, ($$render) => {
		if (get(live)) $$render(consequent);
	});
	reset(div_1);
	var node_1 = sibling(div_1, 2);
	var consequent_1 = ($$anchor) => {
		var div_2 = root_1$3();
		var text_6 = only_child(div_2, true);
		template_effect(() => set_text(text_6, get(error)));
		append($$anchor, div_2);
	};
	if_block(node_1, ($$render) => {
		if (get(error)) $$render(consequent_1);
	});
	var div_3 = sibling(node_1, 2);
	var node_2 = child(div_3);
	each(node_2, 17, () => get(events), (e) => e.seq, ($$anchor, e) => {
		var fragment = comment();
		var node_3 = first_child(fragment);
		var consequent_3 = ($$anchor) => {
			var div_4 = root_3$3();
			let classes_1;
			var node_4 = child(div_4);
			var consequent_2 = ($$anchor) => {
				var span_5 = root_2$3();
				append($$anchor, span_5);
			};
			var d_1 = user_derived(() => get(replies).has(get(e).seq));
			if_block(node_4, ($$render) => {
				if (get(d_1)) $$render(consequent_2);
			});
			var text_7 = sibling(node_4, 1, true);
			reset(div_4);
			template_effect(($0) => {
				classes_1 = set_class(div_4, 1, "tc-ev tc-text", null, classes_1, {
					"tc-sub": get(e).parent,
					"tc-reply": $0
				});
				set_text(text_7, get(e).text);
			}, [() => get(replies).has(get(e).seq)]);
			append($$anchor, div_4);
		};
		var consequent_6 = ($$anchor) => {
			var fragment_1 = comment();
			var node_5 = first_child(fragment_1);
			var consequent_5 = ($$anchor) => {
				var div_5 = root_3$3();
				let classes_2;
				var node_6 = child(div_5);
				var consequent_4 = ($$anchor) => {
					var span_6 = root_2$3();
					append($$anchor, span_6);
				};
				var d_2 = user_derived(() => get(replies).has(get(e).seq));
				if_block(node_6, ($$render) => {
					if (get(d_2)) $$render(consequent_4);
				});
				var text_8 = sibling(node_6, 1, true);
				reset(div_5);
				template_effect(($0) => {
					classes_2 = set_class(div_5, 1, "tc-ev tc-thinking", null, classes_2, {
						"tc-sub": get(e).parent,
						"tc-reply": $0
					});
					set_text(text_8, get(e).text);
				}, [() => get(replies).has(get(e).seq)]);
				append($$anchor, div_5);
			};
			if_block(node_5, ($$render) => {
				if (get(e).text && (!get(e).parent || get(verbose))) $$render(consequent_5);
			});
			append($$anchor, fragment_1);
		};
		var consequent_8 = ($$anchor) => {
			const r = user_derived(() => get(results).get(get(e).id));
			var div_6 = root_5$2();
			let classes_3;
			var button_1 = child(div_6);
			var span_7 = child(button_1);
			var text_9 = only_child(span_7, true);
			var b_1 = sibling(span_7, 2);
			var text_10 = only_child(b_1, true);
			var span_8 = sibling(b_1, 2);
			var text_11 = only_child(span_8, true);
			var span_9 = sibling(span_8, 2);
			var text_12 = only_child(span_9, true);
			reset(button_1);
			var node_7 = sibling(button_1, 2);
			var consequent_7 = ($$anchor) => {
				var pre = root_4$2();
				var text_13 = only_child(pre);
				template_effect(() => set_text(text_13, `${get(e).input ?? ""}${get(r) ? "\n— result —\n" + get(r).excerpt : ""}`));
				append($$anchor, pre);
			};
			if_block(node_7, ($$render) => {
				if (get(open)[get(e).id]) $$render(consequent_7);
			});
			reset(div_6);
			template_effect(() => {
				classes_3 = set_class(div_6, 1, "tc-ev tc-tool", null, classes_3, { "tc-sub": get(e).parent });
				set_attribute(button_1, "aria-expanded", !!get(open)[get(e).id]);
				set_text(text_9, get(open)[get(e).id] ? "▾" : "▸");
				set_text(text_10, get(e).name);
				set_text(text_11, get(e).summary);
				set_class(span_9, 1, `tc-tool-status ${get(r) ? get(r).denied ? "is-denied" : get(r).is_error ? "is-error" : "is-ok" : "is-running"}`);
				set_text(text_12, get(r) ? get(r).denied ? "denied" : get(r).is_error ? "error" : "ok" : "…");
			});
			delegated("click", button_1, () => set(open, {
				...get(open),
				[get(e).id]: !get(open)[get(e).id]
			}, true));
			append($$anchor, div_6);
		};
		var consequent_10 = ($$anchor) => {
			const label = user_derived(() => taskLabel(get(e)));
			var fragment_2 = comment();
			var node_8 = first_child(fragment_2);
			var consequent_9 = ($$anchor) => {
				var div_7 = root_6$2();
				var text_14 = only_child(div_7, true);
				template_effect(() => set_text(text_14, get(label)));
				append($$anchor, div_7);
			};
			if_block(node_8, ($$render) => {
				if (get(label)) $$render(consequent_9);
			});
			append($$anchor, fragment_2);
		};
		var consequent_12 = ($$anchor) => {
			var div_8 = root_8$2();
			let classes_4;
			var text_15 = child(div_8);
			var node_9 = sibling(text_15);
			var consequent_11 = ($$anchor) => {
				var div_9 = root_7$2();
				var text_16 = only_child(div_9);
				template_effect(() => set_text(text_16, `Needs a look: ${get(e).attention ?? ""}`));
				append($$anchor, div_9);
			};
			if_block(node_9, ($$render) => {
				if (get(e).attention) $$render(consequent_11);
			});
			reset(div_8);
			template_effect(() => {
				classes_4 = set_class(div_8, 1, "tc-ev tc-update", null, classes_4, { "tc-attn": !!get(e).attention });
				set_text(text_15, `${get(e).at ? `${get(e).at} ` : ""}${get(e).text ?? ""}`);
			});
			append($$anchor, div_8);
		};
		var consequent_13 = ($$anchor) => {
			var div_10 = root_9$1();
			var text_17 = only_child(div_10, true);
			template_effect(($0) => {
				set_class(div_10, 1, `tc-ev tc-marker ${$0 ?? ""}`);
				set_text(text_17, get(e).line);
			}, [() => markerClass(get(e).line)]);
			append($$anchor, div_10);
		};
		var consequent_15 = ($$anchor) => {
			var div_11 = root_14$1();
			var node_10 = sibling(child(div_11), 2);
			each(node_10, 17, () => get(e).input && get(e).input.questions || [], index, ($$anchor, q) => {
				var fragment_3 = root_13$1();
				var div_12 = first_child(fragment_3);
				var text_18 = only_child(div_12, true);
				var node_11 = sibling(div_12, 2);
				var consequent_14 = ($$anchor) => {
					var div_13 = root_11$1();
					var node_12 = child(div_13);
					each(node_12, 17, () => get(q).options || [], index, ($$anchor, o) => {
						var button_2 = root_10$1();
						var text_19 = only_child(button_2, true);
						template_effect(() => {
							set_attribute(button_2, "title", get(o).description || "");
							set_text(text_19, get(o).label);
						});
						delegated("click", button_2, () => answerQuestion(get(e), get(q), get(o).label));
						append($$anchor, button_2);
					});
					var input_2 = sibling(node_12, 2);
					remove_input_defaults(input_2);
					var button_3 = sibling(input_2, 2);
					reset(div_13);
					bind_value(input_2, () => other[get(e).request_id], ($$value) => other[get(e).request_id] = $$value);
					delegated("click", button_3, () => answerQuestion(get(e), get(q), other[get(e).request_id] || ""));
					append($$anchor, div_13);
				};
				var d_3 = user_derived(() => get(e).waits && get(live) && !get(pendingIds).has(get(e).request_id) && !get(answered)[get(e).request_id]);
				var alternate = ($$anchor) => {
					var div_14 = root_12$1();
					var text_20 = only_child(div_14, true);
					template_effect(() => set_text(text_20, get(answered)[get(e).request_id] ? "Answered here." : get(e).waits ? "Waiting for an answer…" : "Not waited for: the campaign carries on (D5)."));
					append($$anchor, div_14);
				};
				if_block(node_11, ($$render) => {
					if (get(d_3)) $$render(consequent_14);
					else $$render(alternate, -1);
				});
				template_effect(() => set_text(text_18, get(q).question));
				append($$anchor, fragment_3);
			});
			reset(div_11);
			append($$anchor, div_11);
		};
		var consequent_17 = ($$anchor) => {
			var div_15 = root_16();
			var div_16 = child(div_15);
			var text_21 = only_child(div_16);
			var pre_1 = sibling(div_16, 2);
			var text_22 = only_child(pre_1, true);
			var node_13 = sibling(pre_1, 2);
			var consequent_16 = ($$anchor) => {
				var fragment_4 = root_15();
				var button_4 = first_child(fragment_4);
				var button_5 = sibling(button_4, 2);
				delegated("click", button_4, () => approve(get(e), true));
				delegated("click", button_5, () => approve(get(e), false));
				append($$anchor, fragment_4);
			};
			var d_4 = user_derived(() => get(e).waits && get(live) && !get(pendingIds).has(get(e).request_id) && !get(answered)[get(e).request_id]);
			var alternate_1 = ($$anchor) => {
				var div_17 = root_12$1();
				var text_23 = only_child(div_17, true);
				template_effect(() => set_text(text_23, get(answered)[get(e).request_id] ? "Answered here." : "Not approved: outside the session's permission profile (D6)."));
				append($$anchor, div_17);
			};
			if_block(node_13, ($$render) => {
				if (get(d_4)) $$render(consequent_16);
				else $$render(alternate_1, -1);
			});
			reset(div_15);
			template_effect(() => {
				set_text(text_21, `Permission asked: ${get(e).tool ?? ""}`);
				set_text(text_22, get(e).input);
			});
			append($$anchor, div_15);
		};
		var consequent_18 = ($$anchor) => {
			var div_18 = root_17();
			var text_24 = only_child(div_18);
			template_effect(($0, $1) => set_text(text_24, `turn finished · ${get(e).num_turns ?? ""} turns · ${$0 ?? ""}${$1 ?? ""}`), [() => fmtDuration(get(e).duration_ms), () => get(e).total_cost_usd != null ? ` · $${get(e).total_cost_usd.toFixed(2)}` : ""]);
			append($$anchor, div_18);
		};
		var consequent_19 = ($$anchor) => {
			var div_19 = root_18();
			var text_25 = only_child(div_19, true);
			template_effect(() => set_text(text_25, get(e).text));
			append($$anchor, div_19);
		};
		var consequent_20 = ($$anchor) => {
			var div_20 = root_19();
			var text_26 = only_child(div_20);
			template_effect(() => set_text(text_26, `session ${get(e).state ?? ""}${get(e).error ? ": " + get(e).error : ""}`));
			append($$anchor, div_20);
		};
		var consequent_21 = ($$anchor) => {
			var div_21 = root_19();
			var text_27 = only_child(div_21);
			template_effect(() => set_text(text_27, `session started · ${(get(e).model || "") ?? ""} · permission mode ${(get(e).permission_mode || "?") ?? ""} · Claude Code ${(get(e).cli_version || "?") ?? ""}`));
			append($$anchor, div_21);
		};
		if_block(node_3, ($$render) => {
			if (get(e).kind === "text") $$render(consequent_3);
			else if (get(e).kind === "thinking") $$render(consequent_6, 1);
			else if (get(e).kind === "tool_use") $$render(consequent_8, 2);
			else if (get(e).kind === "task") $$render(consequent_10, 3);
			else if (get(e).kind === "update") $$render(consequent_12, 4);
			else if (get(e).kind === "marker") $$render(consequent_13, 5);
			else if (get(e).kind === "question") $$render(consequent_15, 6);
			else if (get(e).kind === "approval") $$render(consequent_17, 7);
			else if (get(e).kind === "result") $$render(consequent_18, 8);
			else if (get(e).kind === "user_message") $$render(consequent_19, 9);
			else if (get(e).kind === "state") $$render(consequent_20, 10);
			else if (get(e).kind === "init") $$render(consequent_21, 11);
		});
		append($$anchor, fragment);
	});
	var node_14 = sibling(node_2, 2);
	var consequent_22 = ($$anchor) => {
		var div_22 = root_20();
		append($$anchor, div_22);
	};
	if_block(node_14, ($$render) => {
		if (!get(events).length) $$render(consequent_22);
	});
	reset(div_3);
	bind_this(div_3, ($$value) => box = $$value, () => box);
	var node_15 = sibling(div_3, 2);
	var consequent_23 = ($$anchor) => {
		var div_23 = root_21();
		var input_3 = child(div_23);
		remove_input_defaults(input_3);
		var button_6 = sibling(input_3, 2);
		reset(div_23);
		delegated("keydown", input_3, (ev) => {
			if (ev.key === "Enter") send();
		});
		bind_value(input_3, () => get(draft), ($$value) => set(draft, $$value));
		delegated("click", button_6, send);
		append($$anchor, div_23);
	};
	if_block(node_15, ($$render) => {
		if (get(live)) $$render(consequent_23);
	});
	reset(div);
	template_effect(($0, $1, $2, $3) => {
		classes = set_class(div, 1, "tc-window", null, classes, { "tc-compact": compact() });
		set_class(span, 1, `tc-badge tc-state-${get(state$1) ?? ""}`);
		set_text(text_1, get(state$1));
		set_text(text_2, get(mode) === "live" ? "live from this seat" : "from the run record");
		set_text(text_3, `time ${$0 ?? ""}`);
		set_text(text_4, `tokens ${$1 ?? ""}`);
		set_attribute(span_4, "title", $2);
		set_text(text_5, $3);
		set_checked(input_1, get(verbose));
	}, [
		() => fmtDuration(get(elapsed)),
		() => fmtTokens(get(tokens)),
		() => `list-price estimate${get(updatesCost) ? `, including $${get(updatesCost).toFixed(2)} for the running updates` : ""}`,
		() => get(cost) != null ? `$${get(cost).toFixed(2)}` : ""
	]);
	bind_checked(input, () => get(follow), ($$value) => set(follow, $$value));
	delegated("change", input_1, (ev) => setVerbose(ev.currentTarget.checked));
	event("scroll", div_3, () => {
		if (box) set(follow, box.scrollHeight - box.scrollTop - box.clientHeight < 40);
	});
	append($$anchor, div);
	pop();
}
delegate([
	"change",
	"click",
	"keydown"
]);
//#endregion
//#region src/tc/LogViewer.svelte
var root$3 = from_html(`<div class="tc-problem"> </div>`);
var root_1$2 = from_html(`<div class="tc-small">No campaign files yet — device-testing writes them as the run goes (its queue file names this run).</div>`);
var root_2$2 = from_html(`<option> </option>`);
var root_3$2 = from_html(`<a class="btn btn-secondary btn-compact-small">Download</a> <button type="button" class="btn btn-secondary btn-compact-small">Copy</button>`, 1);
var root_4$1 = from_html(`<button type="button" class="btn btn-secondary btn-compact-small tc-earlier"> </button>`);
var root_5$1 = from_html(`<span> </span> `, 1);
var root_6$1 = from_html(`<div class="tc-pane"><div class="tc-pane-head"><select class="form-input"><option>— choose a file —</option><!></select> <!></div> <!> <pre class="tc-pre tc-log"></pre></div>`);
var root_7$1 = from_html(`<div class="tc-small"> </div> <div class="tc-panes"></div>`, 1);
var root_8$1 = from_html(`<div class="tc-logs"><!> <!></div>`);
function LogViewer($$anchor, $$props) {
	push($$props, true);
	let caseKey = prop($$props, "caseKey", 3, null);
	let camp = state(null);
	let error = state(null);
	let panes = proxy([{
		path: "",
		text: "",
		start: null,
		more: false,
		busy: false
	}, {
		path: "",
		text: "",
		start: null,
		more: false,
		busy: false
	}]);
	const files = user_derived(() => get(camp) ? get(camp).files.filter((f) => !caseKey() || !f.case || caseKey().endsWith(String(f.case).split("-")[0])) : []);
	async function loadFiles() {
		try {
			set(camp, await $$props.server(`/runs/${encodeURIComponent($$props.runId)}/campaign`), true);
			if (get(camp).found && get(files).length && !panes[0].path) await pick(0, (get(files).find((f) => f.final) || get(files)[get(files).length - 1]).path);
		} catch (e) {
			set(error, e.message, true);
		}
	}
	async function pick(i, path) {
		panes[i] = {
			path,
			text: "",
			start: null,
			more: false,
			busy: true
		};
		if (!path) {
			panes[i].busy = false;
			return;
		}
		try {
			const d = await $$props.server(`/runs/${encodeURIComponent($$props.runId)}/file?path=${encodeURIComponent(path)}`);
			panes[i] = {
				path,
				text: d.data,
				start: d.start,
				more: d.has_more_before,
				busy: false
			};
		} catch (e) {
			panes[i] = {
				...panes[i],
				busy: false
			};
			set(error, e.message, true);
		}
	}
	async function earlier(i) {
		const p = panes[i];
		if (!p.more || p.busy) return;
		panes[i] = {
			...p,
			busy: true
		};
		try {
			const d = await $$props.server(`/runs/${encodeURIComponent($$props.runId)}/file?path=${encodeURIComponent(p.path)}&before=${p.start}`);
			panes[i] = {
				...p,
				text: d.data + p.text,
				start: d.start,
				more: d.has_more_before,
				busy: false
			};
		} catch (e) {
			panes[i] = {
				...p,
				busy: false
			};
			set(error, e.message, true);
		}
	}
	function copy(i) {
		try {
			navigator.clipboard.writeText(panes[i].text);
		} catch (_) {}
	}
	function hl(line) {
		return /\bFAIL\b|UNSUPPORTED|ERROR/.test(line) ? "tc-log-fail" : /\bPASS\b/.test(line) ? "tc-log-pass" : "";
	}
	user_effect(() => {
		loadFiles();
	});
	var div = root_8$1();
	var node = child(div);
	var consequent = ($$anchor) => {
		var div_1 = root$3();
		var text = only_child(div_1, true);
		template_effect(() => set_text(text, get(error)));
		append($$anchor, div_1);
	};
	if_block(node, ($$render) => {
		if (get(error)) $$render(consequent);
	});
	var node_1 = sibling(node, 2);
	var consequent_1 = ($$anchor) => {
		var div_2 = root_1$2();
		append($$anchor, div_2);
	};
	var consequent_4 = ($$anchor) => {
		var fragment = root_7$1();
		var div_3 = first_child(fragment);
		var text_1 = only_child(div_3);
		var div_4 = sibling(div_3, 2);
		each(div_4, 21, () => panes, index, ($$anchor, p, i) => {
			var div_5 = root_6$1();
			var div_6 = child(div_5);
			var select = child(div_6);
			var option = child(select);
			option.value = option.__value = "";
			var node_2 = sibling(option);
			each(node_2, 17, () => get(files), index, ($$anchor, f) => {
				var option_1 = root_2$2();
				var text_2 = only_child(option_1);
				var option_1_value = {};
				template_effect(($0, $1) => {
					set_text(text_2, `${$0 ?? ""} (${$1 ?? ""} KB)${get(f).final ? " · final" : ""}`);
					if (option_1_value !== (option_1_value = get(f).path)) option_1.value = (option_1.__value = option_1_value) ?? "";
				}, [() => get(f).path.split("/").slice(-3).join("/"), () => Math.round(get(f).size / 1024)]);
				append($$anchor, option_1);
			});
			reset(select);
			var select_value;
			init_select(select);
			var node_3 = sibling(select, 2);
			var consequent_2 = ($$anchor) => {
				var fragment_1 = root_3$2();
				var a = first_child(fragment_1);
				var button = sibling(a, 2);
				template_effect(($0) => set_attribute(a, "href", $0), [() => `/api/test-composer/runs/${encodeURIComponent($$props.runId)}/download?path=${encodeURIComponent(get(p).path)}`]);
				delegated("click", button, () => copy(i));
				append($$anchor, fragment_1);
			};
			if_block(node_3, ($$render) => {
				if (get(p).path) $$render(consequent_2);
			});
			reset(div_6);
			var node_4 = sibling(div_6, 2);
			var consequent_3 = ($$anchor) => {
				var button_1 = root_4$1();
				var text_3 = only_child(button_1, true);
				template_effect(() => {
					button_1.disabled = get(p).busy;
					set_text(text_3, get(p).busy ? "Loading…" : "Load earlier");
				});
				delegated("click", button_1, () => earlier(i));
				append($$anchor, button_1);
			};
			if_block(node_4, ($$render) => {
				if (get(p).more) $$render(consequent_3);
			});
			var pre = sibling(node_4, 2);
			each(pre, 21, () => get(p).text.split("\n"), index, ($$anchor, line) => {
				var fragment_2 = root_5$1();
				var span = first_child(fragment_2);
				var text_4 = only_child(span, true);
				var text_5 = sibling(span, 1, true);
				text_5.nodeValue = "\n";
				template_effect(($0) => {
					set_class(span, 1, $0);
					set_text(text_4, get(line));
				}, [() => clsx(hl(get(line)))]);
				append($$anchor, fragment_2);
			});
			reset(pre);
			reset(div_5);
			template_effect(() => {
				if (select_value !== (select_value = get(p).path)) select.value = (select.__value = select_value) ?? "", select_option(select, select_value);
			});
			delegated("change", select, (e) => pick(i, e.currentTarget.value));
			append($$anchor, div_5);
		});
		reset(div_4);
		template_effect(() => set_text(text_1, `Queue: ${get(camp).queue ?? ""} · ${get(files).length ?? ""} file(s)`));
		append($$anchor, fragment);
	};
	if_block(node_1, ($$render) => {
		if (get(camp) && !get(camp).found) $$render(consequent_1);
		else if (get(camp)) $$render(consequent_4, 1);
	});
	reset(div);
	append($$anchor, div);
	pop();
}
delegate(["change", "click"]);
//#endregion
//#region src/tc/ResultsTable.svelte
var root$2 = from_html(`<div class="tc-problem"> </div>`);
var root_1$1 = from_html(`<span><b> </b> </span>`);
var root_2$1 = from_html(`<div class="tc-small"> </div>`);
var root_3$1 = from_html(`<button type="button" class="btn btn-primary btn-compact-small"> </button>`);
var root_4 = from_html(`<option> </option>`);
var root_5 = from_html(`<tr class="tc-subrow"><td colspan="5"><select class="form-input"></select> <input class="form-input" placeholder="why (kept beside the framework's verdict)"/> <button type="button" class="btn btn-primary btn-compact-small">Save</button> <button type="button" class="btn btn-secondary btn-compact-small">Cancel</button></td></tr>`);
var root_6 = from_html(`<tr class="tc-subrow"><td colspan="5"><div class="tc-feedback"><!> <pre class="tc-pre"> </pre></div></td></tr>`);
var root_7 = from_html(`<tr class="tc-subrow"><td colspan="5"><!></td></tr>`);
var root_8 = from_html(`<tr><td><span class="tc-key"> </span></td><td><span> </span></td><td><span> </span> <!></td><td class="tc-reason"> </td><td class="tc-actions"><button type="button" class="btn btn-secondary btn-compact-small">Logs</button> <button type="button" class="btn btn-secondary btn-compact-small">Re-grade</button> <!></td></tr> <!> <!> <!>`, 1);
var root_9 = from_html(`<div class="tc-cycle"> </div> <table class="table tc-results"><thead><tr><th>Case</th><th>Type</th><th>Verdict</th><th>Reason</th><th></th></tr></thead><tbody></tbody></table>`, 1);
var root_10 = from_html(`<span class="tc-small"> </span>`);
var root_11 = from_html(`<button type="button" class="btn btn-secondary" title="The evidence (work/ folders) is kept until you accept">Accept results</button>`);
var root_12 = from_html(`<div class="tc-accept"><!></div>`);
var root_13 = from_html(`<div class="tc-readout"><!> <span class="tc-spacer"></span> <span class="tc-small">time <b> </b></span> <span class="tc-small">tokens <b> </b></span> <span class="tc-small"> </span> <span> </span></div> <!> <!>`, 1);
var root_14 = from_html(`<!> <!>`, 1);
function ResultsTable($$anchor, $$props) {
	push($$props, true);
	let refreshMs = prop($$props, "refreshMs", 3, 5e3);
	let data = state(null);
	let error = state(null);
	let fb = state(proxy({}));
	let regrading = state(null);
	let rg = state(proxy({
		verdict: "PASS",
		note: ""
	}));
	let logOpen = state(null);
	let timer = null;
	const table = user_derived(() => get(data) ? get(data).table : []);
	const groups = user_derived(() => byCycle(get(table)));
	const counts = user_derived(() => verdictCounts(get(table)));
	const rec = user_derived(() => get(data) ? get(data).record : null);
	const duration = user_derived(() => get(rec) && get(rec).started ? (get(rec).ended ? Date.parse(get(rec).ended) : Date.now()) - Date.parse(get(rec).started) : null);
	async function load() {
		try {
			set(data, await $$props.server(`/runs/${encodeURIComponent($$props.runId)}`), true);
			set(error, null);
		} catch (e) {
			set(error, e.message, true);
		}
	}
	async function feedback(row) {
		set(fb, {
			...get(fb),
			[row.case]: { busy: true }
		}, true);
		try {
			const d = await $$props.server(`/runs/${encodeURIComponent($$props.runId)}/feedback/${encodeURIComponent(row.case)}`, { method: "POST" });
			set(fb, {
				...get(fb),
				[row.case]: {
					text: d.text,
					error: d.error
				}
			}, true);
		} catch (e) {
			set(fb, {
				...get(fb),
				[row.case]: { error: e.message }
			}, true);
		}
	}
	async function saveRegrade(row) {
		try {
			await $$props.server(`/runs/${encodeURIComponent($$props.runId)}/regrade`, {
				method: "POST",
				body: JSON.stringify({
					case: row.case,
					verdict: get(rg).verdict,
					note: get(rg).note
				})
			});
			set(regrading, null);
			await load();
		} catch (e) {
			set(error, e.message, true);
		}
	}
	async function accept() {
		try {
			await $$props.server(`/runs/${encodeURIComponent($$props.runId)}/accept`, { method: "POST" });
			await load();
		} catch (e) {
			set(error, e.message, true);
		}
	}
	user_effect(() => {
		load();
		timer = setInterval(() => {
			if (!get(rec) || ![
				"done",
				"stopped",
				"error"
			].includes(get(rec).state)) load();
		}, refreshMs());
		return () => clearInterval(timer);
	});
	var fragment = root_14();
	var node = first_child(fragment);
	var consequent = ($$anchor) => {
		var div = root$2();
		var text = only_child(div, true);
		template_effect(() => set_text(text, get(error)));
		append($$anchor, div);
	};
	if_block(node, ($$render) => {
		if (get(error)) $$render(consequent);
	});
	var node_1 = sibling(node, 2);
	var consequent_9 = ($$anchor) => {
		var fragment_1 = root_13();
		var div_1 = first_child(fragment_1);
		var node_2 = child(div_1);
		each(node_2, 17, () => get(counts), index, ($$anchor, c) => {
			var span = root_1$1();
			var b = child(span);
			var text_1 = only_child(b, true);
			var text_2 = sibling(b);
			reset(span);
			template_effect(($0) => {
				set_class(span, 1, `tc-count tc-v-${$0 ?? ""}`);
				set_text(text_1, get(c).n);
				set_text(text_2, ` ${get(c).verdict ?? ""}`);
			}, [() => get(c).verdict.replace(" ", "-")]);
			append($$anchor, span);
		});
		var span_1 = sibling(node_2, 4);
		var b_1 = sibling(child(span_1));
		var text_3 = only_child(b_1, true);
		reset(span_1);
		var span_2 = sibling(span_1, 2);
		var b_2 = sibling(child(span_2));
		var text_4 = only_child(b_2, true);
		reset(span_2);
		var span_3 = sibling(span_2, 2);
		var text_5 = only_child(span_3, true);
		var span_4 = sibling(span_3, 2);
		var text_6 = only_child(span_4, true);
		reset(div_1);
		var node_3 = sibling(div_1, 2);
		each(node_3, 17, () => get(groups), index, ($$anchor, g) => {
			var fragment_2 = root_9();
			var div_2 = first_child(fragment_2);
			var text_7 = only_child(div_2, true);
			var table_1 = sibling(div_2, 2);
			var tbody = sibling(child(table_1));
			each(tbody, 21, () => get(g).rows, (row) => row.case, ($$anchor, row) => {
				const v = user_derived(() => effectiveVerdict(get(row)));
				var fragment_3 = root_8();
				var tr = first_child(fragment_3);
				var td = child(tr);
				var span_5 = child(td);
				var text_8 = only_child(span_5, true);
				reset(td);
				var td_1 = sibling(td);
				var span_6 = child(td_1);
				var text_9 = only_child(span_6, true);
				reset(td_1);
				var td_2 = sibling(td_1);
				var span_7 = child(td_2);
				var text_10 = only_child(span_7, true);
				var node_4 = sibling(span_7, 2);
				var consequent_1 = ($$anchor) => {
					var div_3 = root_2$1();
					var text_11 = only_child(div_3);
					template_effect(() => {
						set_attribute(div_3, "title", get(row).regrade.note);
						set_text(text_11, `re-graded from ${get(row).verdict ?? ""} by ${get(row).regrade.by ?? ""}`);
					});
					append($$anchor, div_3);
				};
				if_block(node_4, ($$render) => {
					if (get(row).regrade) $$render(consequent_1);
				});
				reset(td_2);
				var td_3 = sibling(td_2);
				var text_12 = only_child(td_3, true);
				var td_4 = sibling(td_3);
				var button = child(td_4);
				var button_1 = sibling(button, 2);
				var node_5 = sibling(button_1, 2);
				var consequent_2 = ($$anchor) => {
					var button_2 = root_3$1();
					var text_13 = only_child(button_2, true);
					template_effect(() => {
						button_2.disabled = get(fb)[get(row).case] && get(fb)[get(row).case].busy;
						set_text(text_13, get(fb)[get(row).case] && get(fb)[get(row).case].busy ? "Asking…" : "Feedback");
					});
					delegated("click", button_2, () => feedback(get(row)));
					append($$anchor, button_2);
				};
				var d_1 = user_derived(() => get(row).kind === "script" && [
					"FAIL",
					"ERROR",
					"PARTIAL"
				].includes(get(row).verdict));
				if_block(node_5, ($$render) => {
					if (get(d_1)) $$render(consequent_2);
				});
				reset(td_4);
				reset(tr);
				var node_6 = sibling(tr, 2);
				var consequent_3 = ($$anchor) => {
					var tr_1 = root_5();
					var td_5 = child(tr_1);
					var select = child(td_5);
					each(select, 21, () => VERDICT_ORDER.filter((x) => x !== "PENDING"), index, ($$anchor, x) => {
						var option = root_4();
						var text_14 = only_child(option, true);
						var option_value = {};
						template_effect(() => {
							set_text(text_14, get(x));
							if (option_value !== (option_value = get(x))) option.value = (option.__value = option_value) ?? "";
						});
						append($$anchor, option);
					});
					reset(select);
					init_select(select);
					var input = sibling(select, 2);
					remove_input_defaults(input);
					var button_3 = sibling(input, 2);
					var button_4 = sibling(button_3, 2);
					reset(td_5);
					reset(tr_1);
					bind_select_value(select, () => get(rg).verdict, ($$value) => get(rg).verdict = $$value);
					bind_value(input, () => get(rg).note, ($$value) => get(rg).note = $$value);
					delegated("click", button_3, () => saveRegrade(get(row)));
					delegated("click", button_4, () => set(regrading, null));
					append($$anchor, tr_1);
				};
				if_block(node_6, ($$render) => {
					if (get(regrading) === get(row).case) $$render(consequent_3);
				});
				var node_7 = sibling(node_6, 2);
				var consequent_5 = ($$anchor) => {
					var tr_2 = root_6();
					var td_6 = child(tr_2);
					var div_4 = child(td_6);
					var node_8 = child(div_4);
					var consequent_4 = ($$anchor) => {
						var div_5 = root$2();
						var text_15 = only_child(div_5, true);
						template_effect(() => set_text(text_15, get(fb)[get(row).case].error));
						append($$anchor, div_5);
					};
					if_block(node_8, ($$render) => {
						if (get(fb)[get(row).case].error) $$render(consequent_4);
					});
					var pre = sibling(node_8, 2);
					var text_16 = only_child(pre, true);
					reset(div_4);
					reset(td_6);
					reset(tr_2);
					template_effect(() => set_text(text_16, get(fb)[get(row).case].text || ""));
					append($$anchor, tr_2);
				};
				if_block(node_7, ($$render) => {
					if (get(fb)[get(row).case] && (get(fb)[get(row).case].text || get(fb)[get(row).case].error)) $$render(consequent_5);
				});
				var node_9 = sibling(node_7, 2);
				var consequent_6 = ($$anchor) => {
					var tr_3 = root_7();
					var td_7 = child(tr_3);
					LogViewer(child(td_7), {
						get runId() {
							return $$props.runId;
						},
						get server() {
							return $$props.server;
						},
						get caseKey() {
							return get(row).case;
						}
					});
					reset(td_7);
					reset(tr_3);
					append($$anchor, tr_3);
				};
				if_block(node_9, ($$render) => {
					if (get(logOpen) === get(row).case) $$render(consequent_6);
				});
				template_effect(($0) => {
					set_text(text_8, get(row).case);
					set_class(span_6, 1, `tc-kind tc-kind-${get(row).kind ?? ""}`);
					set_text(text_9, get(row).kind === "script" ? "PyScript" : get(row).kind === "manual" ? "Manual" : get(row).kind);
					set_class(span_7, 1, `tc-verdict tc-v-${$0 ?? ""}`);
					set_text(text_10, get(v));
					set_text(text_12, get(row).reason);
				}, [() => get(v).replace(" ", "-")]);
				delegated("click", button, () => set(logOpen, get(logOpen) === get(row).case ? null : get(row).case, true));
				delegated("click", button_1, () => {
					set(regrading, get(row).case, true);
					set(rg, {
						verdict: get(v),
						note: ""
					}, true);
				});
				append($$anchor, fragment_3);
			});
			reset(tbody);
			reset(table_1);
			template_effect(() => set_text(text_7, get(g).cycle ? `Cycle ${get(g).cycle}` : "No cycle"));
			append($$anchor, fragment_2);
		});
		var node_11 = sibling(node_3, 2);
		var consequent_8 = ($$anchor) => {
			var div_6 = root_12();
			var node_12 = child(div_6);
			var consequent_7 = ($$anchor) => {
				var span_8 = root_10();
				var text_17 = only_child(span_8);
				template_effect(() => set_text(text_17, `Results accepted ${get(rec).accepted_at ?? ""}. The campaign's work/ folders are kept until device-testing acts on it.`));
				append($$anchor, span_8);
			};
			var alternate = ($$anchor) => {
				var button_5 = root_11();
				delegated("click", button_5, accept);
				append($$anchor, button_5);
			};
			if_block(node_12, ($$render) => {
				if (get(rec).accepted_at) $$render(consequent_7);
				else $$render(alternate, -1);
			});
			reset(div_6);
			append($$anchor, div_6);
		};
		var d_2 = user_derived(() => [
			"done",
			"stopped",
			"error"
		].includes(get(rec).state));
		if_block(node_11, ($$render) => {
			if (get(d_2)) $$render(consequent_8);
		});
		template_effect(($0, $1, $2) => {
			set_text(text_3, $0);
			set_text(text_4, $1);
			set_text(text_5, $2);
			set_class(span_4, 1, `tc-badge tc-state-${get(rec).state ?? ""}`);
			set_text(text_6, get(rec).state);
		}, [
			() => fmtDuration(get(duration)),
			() => fmtTokens(get(rec).tokens),
			() => get(rec).cost_usd != null || get(rec).updates_cost_usd ? `$${((get(rec).cost_usd || 0) + (get(rec).updates_cost_usd || 0)).toFixed(2)} (list)` : ""
		]);
		append($$anchor, fragment_1);
	};
	if_block(node_1, ($$render) => {
		if (get(rec)) $$render(consequent_9);
	});
	append($$anchor, fragment);
	pop();
}
delegate(["click"]);
//#endregion
//#region src/tc/RunsList.svelte
var root$1 = from_html(`<div class="tc-problem"> </div>`);
var root_1 = from_html(`<div class="tc-small">No runs yet.</div>`);
var root_2 = from_html(`<button type="button" class="tc-run-row"><span class="tc-key"> </span> <span> </span> <span class="tc-small"> </span> <span class="tc-small"> </span> <span class="tc-small"> </span></button>`);
var root_3 = from_html(`<div class="tc-runs"><!> <!> <!></div>`);
function RunsList($$anchor, $$props) {
	push($$props, true);
	let refreshKey = prop($$props, "refreshKey", 3, 0);
	let runs = state(proxy([]));
	let error = state(null);
	async function load() {
		try {
			set(runs, (await $$props.server(`/runs?kind=${encodeURIComponent($$props.kind)}&limit=25`)).runs, true);
			set(error, null);
		} catch (e) {
			set(error, e.message, true);
		}
	}
	user_effect(() => {
		refreshKey();
		load();
	});
	var div = root_3();
	var node = child(div);
	var consequent = ($$anchor) => {
		var div_1 = root$1();
		var text = only_child(div_1, true);
		template_effect(() => set_text(text, get(error)));
		append($$anchor, div_1);
	};
	if_block(node, ($$render) => {
		if (get(error)) $$render(consequent);
	});
	var node_1 = sibling(node, 2);
	var consequent_1 = ($$anchor) => {
		var div_2 = root_1();
		append($$anchor, div_2);
	};
	if_block(node_1, ($$render) => {
		if (!get(runs).length) $$render(consequent_1);
	});
	var node_2 = sibling(node_1, 2);
	each(node_2, 17, () => get(runs), (r) => r.run_id, ($$anchor, r) => {
		var button = root_2();
		var span = child(button);
		var text_1 = only_child(span, true);
		var span_1 = sibling(span, 2);
		var text_2 = only_child(span_1, true);
		var span_2 = sibling(span_1, 2);
		var text_3 = only_child(span_2);
		var span_3 = sibling(span_2, 2);
		var text_4 = only_child(span_3, true);
		var span_4 = sibling(span_3, 2);
		var text_5 = only_child(span_4, true);
		reset(button);
		template_effect(($0, $1, $2) => {
			set_text(text_1, get(r).run_id);
			set_class(span_1, 1, `tc-badge tc-state-${get(r).state ?? ""}`);
			set_text(text_2, get(r).state);
			set_text(text_3, `${get(r).testbox ?? ""} · ${$0 ?? ""}`);
			set_text(text_4, $1);
			set_text(text_5, $2);
		}, [
			() => (get(r).cases || []).join(", ") || "no cases",
			() => Object.entries(get(r).counts || {}).map(([k, v]) => `${v} ${k}`).join(", "),
			() => get(r).tokens ? `${fmtTokens(get(r).tokens)} tokens` : ""
		]);
		delegated("click", button, () => $$props.onopen(get(r).run_id));
		append($$anchor, button);
	});
	reset(div);
	append($$anchor, div);
	pop();
}
delegate(["click"]);
//#endregion
//#region src/tc/SetupFields.svelte
var root = from_html(`<div class="tc-fields"><div class="tc-field"><label for="tc-testbox">Test bench</label> <input id="tc-testbox" class="form-input" placeholder="tb470"/></div> <div class="tc-field tc-wide"><label for="tc-consoles">Consoles this run may use</label> <input id="tc-consoles" class="form-input" placeholder="u0-u5 (u0 = x230 DUT; …)"/></div> <div class="tc-field"><label for="tc-pdu">PDU IP (blank = no PDU)</label> <input id="tc-pdu" class="form-input" placeholder="10.36.150.14"/></div> <div class="tc-field tc-wide"><label for="tc-outlets">PDU outlets</label> <input id="tc-outlets" class="form-input" placeholder="u0=1, u1=7, u2=6"/></div> <div class="tc-field tc-full"><label for="tc-constraints">Session constraints (verbatim to the session)</label> <input id="tc-constraints" class="form-input" placeholder="e.g. shared box: read-only probe; no reloads before 17:00"/></div> <div class="tc-field tc-wide"><label for="tc-email">Email when done / on a notice</label> <input id="tc-email" class="form-input" placeholder="first.last@alliedtelesis.co.nz"/></div></div>`);
function SetupFields($$anchor, $$props) {
	push($$props, true);
	let setup = prop($$props, "setup", 15);
	var div = root();
	var div_1 = child(div);
	var input = sibling(child(div_1), 2);
	remove_input_defaults(input);
	reset(div_1);
	var div_2 = sibling(div_1, 2);
	var input_1 = sibling(child(div_2), 2);
	remove_input_defaults(input_1);
	reset(div_2);
	var div_3 = sibling(div_2, 2);
	var input_2 = sibling(child(div_3), 2);
	remove_input_defaults(input_2);
	reset(div_3);
	var div_4 = sibling(div_3, 2);
	var input_3 = sibling(child(div_4), 2);
	remove_input_defaults(input_3);
	reset(div_4);
	var div_5 = sibling(div_4, 2);
	var input_4 = sibling(child(div_5), 2);
	remove_input_defaults(input_4);
	reset(div_5);
	var div_6 = sibling(div_5, 2);
	var input_5 = sibling(child(div_6), 2);
	remove_input_defaults(input_5);
	reset(div_6);
	reset(div);
	bind_value(input, () => setup().testbox, ($$value) => setup(setup().testbox = $$value, true));
	bind_value(input_1, () => setup().consoles, ($$value) => setup(setup().consoles = $$value, true));
	bind_value(input_2, () => setup().pduIp, ($$value) => setup(setup().pduIp = $$value, true));
	bind_value(input_3, () => setup().outlets, ($$value) => setup(setup().outlets = $$value, true));
	bind_value(input_4, () => setup().constraints, ($$value) => setup(setup().constraints = $$value, true));
	bind_value(input_5, () => setup().email, ($$value) => setup(setup().email = $$value, true));
	append($$anchor, div);
	pop();
}
//#endregion
export { saveSetup as _, TC_API as a, verdictCounts as b, effectiveVerdict as c, formatOutlets as d, httpAgent as f, runBody as g, parseOutlets as h, AgentWindow as i, fmtDuration as l, loadSetup as m, RunsList as n, VERDICT_ORDER as o, httpServer as p, ResultsTable as r, byCycle as s, SetupFields as t, fmtTokens as u, scriptsLink as v, tokensOf as y };
