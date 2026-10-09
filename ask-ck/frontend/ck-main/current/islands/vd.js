/* Built from ask-ck/frontend/ck-main/current/svelte-src/ — do not edit; run `npm run build` there.
* source-sha256:e70afbb2295891a4c61e432045cc3e0508a68b02a22bc5f5391fec2df5e04f6f */
import { B as proxy, C as unmount, D as text, E as from_html, G as pop, H as state, I as child, J as reset, K as push, L as first_child, N as template_effect, O as delegate, R as only_child, S as set_text, U as flushSync, V as set, W as user_derived, _ as each, b as if_block, c as remove_input_defaults, h as set_class, j as get, k as delegated, n as onMount, o as bind_group, r as prop, v as index, w as append, x as mount, y as key, z as sibling } from "./disclose-version-BND4hK_m.js";
import { _ as saveSetup, f as httpAgent, g as runBody, i as AgentWindow, m as loadSetup, n as RunsList, p as httpServer, r as ResultsTable, t as SetupFields } from "./SetupFields-8IINZYsY.js";
//#region src/vd/VdPage.svelte
var root = from_html(`<span class="tc-badge tc-state-done">finalized</span>`);
var root_1 = from_html(`<label><input type="radio" name="vd-script"/> <span class="tc-key"> </span> <span> </span> <span class="tc-small"> </span> <!></label>`);
var root_2 = from_html(`<div class="tc-small">No saved scripts — save one from the PyTest Creator first.</div>`);
var root_3 = from_html(`<!> <div class="tc-step"><span class="tc-step-n">5</span> Results</div> <!>`, 1);
var root_4 = from_html(`<pre class="tc-pre"> </pre>`);
var root_5 = from_html(`<button type="button" class="btn btn-secondary btn-compact-small">Read the review</button>`);
var root_6 = from_html(`<div class="tc-card"><div class="tc-card-head"> </div> <!></div>`);
var root_7 = from_html(`<button type="button" class="btn btn-secondary btn-compact-small">Compare with the saved script</button>`);
var root_8 = from_html(`<span class="tc-small">Loading…</span>`);
var root_9 = from_html(`<div class="tc-problem"> </div>`);
var root_10 = from_html(`<span class="tc-check">✓ saved to the PyTest Creator</span>`);
var root_11 = from_html(`<button type="button" class="btn btn-primary btn-compact-small vd-approve">Approve → save</button>`);
var root_12 = from_html(`<div class="tc-small"> </div> <div class="tc-panes"><pre class="tc-pre tc-log"> </pre><pre class="tc-pre tc-log"> </pre></div> <!>`, 1);
var root_13 = from_html(`<!> <!>`, 1);
var root_14 = from_html(`<div class="tc-card"><div class="tc-card-head"> </div> <div class="tc-small"> </div> <!></div>`);
var root_15 = from_html(`<div class="tc-small">No repaired copy or review yet — both appear here when the session reports them.</div>`);
var root_16 = from_html(`<li> </li>`);
var root_17 = from_html(`<div class="tc-step"><span class="tc-step-n">4</span> </div> <!> <div class="tc-step"><span class="tc-step-n">6</span> Review and repaired copy</div> <!> <!> <!> <div class="tc-step"><span class="tc-step-n">7</span> Finalize</div> <div class="tc-line"><button type="button" id="vd-finalize" class="btn btn-primary" disabled="">Finalize</button> <ul class="tc-blockers"></ul></div>`, 1);
var root_18 = from_html(`<div class="section tc-page"><div class="section-heading">Validation</div> <div class="section-description">Run one saved script on a test bench through your seat's agent. The session probes the bench, checks the script's topology needs, runs it, repairs a <i>copy</i> until the run is clean, and reviews it. Nothing changes the saved script until you approve; Finalize then marks the case automatable in Zephyr and takes it off the authoring lists.</div> <div class="tc-step"><span class="tc-step-n">1</span> Script</div> <div class="tc-scripts"><!> <!></div> <div class="tc-step"><span class="tc-step-n">2</span> Where it runs</div> <!> <div class="tc-step"><span class="tc-step-n">3</span> Launch</div> <div class="tc-line"><button type="button" id="vd-launch" class="btn btn-primary"> </button> <span class="tc-small"><!></span></div> <div role="status"> </div> <!> <div class="tc-step">Earlier Validation runs</div> <!></div>`);
function VdPage($$anchor, $$props) {
	push($$props, true);
	const binding_group = [];
	let preselect = prop($$props, "preselect", 3, null), openRun = prop($$props, "openRun", 3, null), saveScript = prop($$props, "saveScript", 3, defaultSave), pollMs = prop($$props, "pollMs", 3, 5e3);
	/** Approval goes through the PyTest Creator's own save, so its units⇄script binding reports the edit. */
	async function defaultSave(caseKey, code) {
		const r = await fetch(`/api/pytest-create/save_script/${encodeURIComponent(caseKey)}`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ code })
		});
		const d = await r.json().catch(() => ({}));
		if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : `HTTP ${r.status}`);
		return d;
	}
	let scripts = state(proxy([]));
	let chosen = state(null);
	let setup = state(proxy(Object.assign({
		testbox: "",
		consoles: "",
		pduIp: "",
		outlets: "",
		constraints: "",
		email: ""
	}, loadSetup())));
	let health = state(null);
	let busy = state(false);
	let status = state(proxy({
		msg: "",
		bad: false
	}));
	let run = state(null);
	let runState = state(null);
	let refreshKey = state(0);
	let markers = state(proxy([]));
	const script = user_derived(() => get(scripts).find((s) => s.path === get(chosen)));
	const sessionsOk = user_derived(() => get(health) && get(health).sessions && get(health).sessions.available);
	const canLaunch = user_derived(() => !!get(script) && get(sessionsOk) && get(setup).testbox && get(setup).consoles && !get(busy));
	const parse = (l) => {
		const [, c, ...p] = l.split(/\s+/);
		return {
			case: c,
			path: p.join(" ")
		};
	};
	const repaired = user_derived(() => get(markers).filter((l) => l.startsWith("REPAIRED ")).map(parse));
	const reviews = user_derived(() => get(markers).filter((l) => l.startsWith("REVIEWED ")).map(parse));
	const reviewed = user_derived(() => get(reviews).length > 0);
	let compare = state(proxy({}));
	let reviewText = state(proxy({}));
	async function loadCompare(r) {
		set(compare, {
			...get(compare),
			[r.path]: { busy: true }
		}, true);
		try {
			const d = await $$props.server(`/runs/${encodeURIComponent(get(run).runId)}/repaired?path=${encodeURIComponent(r.path)}&case=${encodeURIComponent(r.case)}`);
			set(compare, {
				...get(compare),
				[r.path]: {
					code: d.code,
					original: d.original
				}
			}, true);
		} catch (e) {
			set(compare, {
				...get(compare),
				[r.path]: { error: e.message }
			}, true);
		}
	}
	async function approve(r) {
		const c = get(compare)[r.path];
		if (!c || !c.code) return;
		try {
			await saveScript()(r.case, c.code);
			set(compare, {
				...get(compare),
				[r.path]: {
					...c,
					saved: true
				}
			}, true);
		} catch (e) {
			set(compare, {
				...get(compare),
				[r.path]: {
					...c,
					error: `Not saved: ${e.message}. Open ${r.case} in the PyTest Creator (it holds the case), then approve again.`
				}
			}, true);
		}
	}
	async function loadReview(r) {
		try {
			set(reviewText, {
				...get(reviewText),
				[r.path]: (await $$props.server(`/runs/${encodeURIComponent(get(run).runId)}/file?path=${encodeURIComponent(r.path)}`)).data
			}, true);
		} catch (e) {
			set(reviewText, {
				...get(reviewText),
				[r.path]: "Could not read the review: " + e.message
			}, true);
		}
	}
	/** Changed-line count between two texts (a quick summary, not a full diff). */
	function changed(a, b) {
		const A = (a || "").split("\n"), B = (b || "").split("\n");
		const setA = new Set(A), setB = new Set(B);
		return {
			removed: A.filter((x) => !setB.has(x)).length,
			added: B.filter((x) => !setA.has(x)).length
		};
	}
	const finalizeBlockers = user_derived(() => [
		!get(run) && "no run yet",
		get(run) && get(runState) !== "done" && "the latest run has not finished cleanly",
		get(repaired).some((r) => !(get(compare)[r.path] && get(compare)[r.path].saved)) && "a repaired copy is waiting for your approval",
		!get(reviewed) && "the review has not been written yet (test-mode §11.2)",
		"Zephyr's \"new version\" request is not captured yet (V0) — Finalize writes nothing until it is"
	].filter(Boolean));
	function setStatus(msg, bad = false) {
		set(status, {
			msg,
			bad
		}, true);
	}
	async function loadScripts() {
		try {
			set(scripts, (await $$props.server("/scripts")).scripts, true);
			if (preselect()) set(chosen, (get(scripts).find((s) => s.path === preselect() || s.case_key === preselect()) || {}).path || get(chosen), true);
		} catch (e) {
			setStatus("Could not list scripts: " + e.message, true);
		}
	}
	async function checkAgent() {
		try {
			set(health, await $$props.agent.health(), true);
		} catch (e) {
			set(health, { error: e.message }, true);
		}
	}
	async function launch() {
		if (!get(canLaunch)) return;
		set(busy, true);
		saveSetup(get(setup));
		try {
			const body = runBody("validation", get(setup), { cases: [{
				key: get(script).case_key,
				kind: "script",
				script: get(script).path
			}] });
			const created = await $$props.server("/runs", {
				method: "POST",
				body: JSON.stringify(body)
			});
			const started = await $$props.agent.start({
				run_id: created.run_id,
				handoff: created.handoff,
				mode: "campaign"
			});
			if (!started.ok) throw new Error(started.error || "the seat agent refused the session");
			set(run, {
				runId: created.run_id,
				sessionId: started.session_id
			}, true);
			set(markers, [], true);
			set(refreshKey, get(refreshKey) + 1);
			setStatus(`Launched ${created.run_id} on ${body.testbox}.`);
		} catch (e) {
			setStatus("Launch failed: " + e.message, true);
		} finally {
			set(busy, false);
		}
	}
	async function watchMarkers() {
		if (!get(run)) return;
		try {
			const d = await $$props.server(`/runs/${encodeURIComponent(get(run).runId)}/events`);
			set(markers, d.events.filter((e) => e.kind === "marker").map((e) => e.line), true);
		} catch (_) {}
	}
	onMount(() => {
		loadScripts();
		checkAgent();
		if (openRun()) set(run, {
			runId: openRun(),
			sessionId: null
		}, true);
		const t = setInterval(watchMarkers, pollMs());
		return () => clearInterval(t);
	});
	var div = root_18();
	var div_1 = sibling(child(div), 6);
	var node = child(div_1);
	each(node, 17, () => get(scripts), (s) => s.path, ($$anchor, s) => {
		var label = root_1();
		let classes;
		var input = child(label);
		remove_input_defaults(input);
		var input_value;
		var span = sibling(input, 2);
		var text = only_child(span, true);
		var span_1 = sibling(span, 2);
		var text_1 = only_child(span_1, true);
		var span_2 = sibling(span_1, 2);
		var text_2 = only_child(span_2);
		var node_1 = sibling(span_2, 2);
		var consequent = ($$anchor) => {
			var span_3 = root();
			append($$anchor, span_3);
		};
		if_block(node_1, ($$render) => {
			if (get(s).finalized_at) $$render(consequent);
		});
		reset(label);
		template_effect(($0) => {
			classes = set_class(label, 1, "tc-script-row", null, classes, { "is-chosen": get(chosen) === get(s).path });
			if (input_value !== (input_value = get(s).path)) input.value = (input.__value = input_value) ?? "";
			set_text(text, get(s).case_key || "?");
			set_text(text_1, get(s).path);
			set_text(text_2, `saved ${$0 ?? ""} · ${(get(s).iterations || 0) ?? ""} iteration(s)`);
		}, [() => String(get(s).saved_at || "").slice(0, 10)]);
		bind_group(binding_group, [], input, () => {
			get(s).path;
			return get(chosen);
		}, ($$value) => set(chosen, $$value));
		append($$anchor, label);
	});
	var node_2 = sibling(node, 2);
	var consequent_1 = ($$anchor) => {
		var div_2 = root_2();
		append($$anchor, div_2);
	};
	if_block(node_2, ($$render) => {
		if (!get(scripts).length) $$render(consequent_1);
	});
	reset(div_1);
	var node_3 = sibling(div_1, 4);
	SetupFields(node_3, {
		get setup() {
			return get(setup);
		},
		set setup($$value) {
			set(setup, $$value, true);
		}
	});
	var div_3 = sibling(node_3, 4);
	var button = child(div_3);
	var text_3 = only_child(button, true);
	var span_4 = sibling(button, 2);
	var node_4 = child(span_4);
	var consequent_2 = ($$anchor) => {
		var text_4 = text("checking your seat agent…");
		append($$anchor, text_4);
	};
	var consequent_3 = ($$anchor) => {
		var text_5 = text();
		template_effect(() => set_text(text_5, `Your seat agent is not reachable (${get(health).error ?? ""}) — run the seat setup from the home page.`));
		append($$anchor, text_5);
	};
	var consequent_4 = ($$anchor) => {
		var text_6 = text();
		template_effect(() => set_text(text_6, `Your seat agent cannot run sessions: ${(get(health).sessions ? get(health).sessions.reason : "agent too old — re-run the seat setup") ?? ""}`));
		append($$anchor, text_6);
	};
	var alternate = ($$anchor) => {
		var text_7 = text();
		template_effect(() => set_text(text_7, `Seat agent ${get(health).agent_version ?? ""} ready · Agent SDK ${get(health).sessions.sdk_version ?? ""} · device-testing at ${get(health).sessions.dt_root ?? ""}`));
		append($$anchor, text_7);
	};
	if_block(node_4, ($$render) => {
		if (!get(health)) $$render(consequent_2);
		else if (get(health).error) $$render(consequent_3, 1);
		else if (!get(sessionsOk)) $$render(consequent_4, 2);
		else $$render(alternate, -1);
	});
	reset(span_4);
	reset(div_3);
	var div_4 = sibling(div_3, 2);
	let classes_1;
	var text_8 = only_child(div_4, true);
	var node_5 = sibling(div_4, 2);
	var consequent_12 = ($$anchor) => {
		var fragment_3 = root_17();
		var div_5 = first_child(fragment_3);
		var text_9 = sibling(child(div_5));
		reset(div_5);
		var node_6 = sibling(div_5, 2);
		key(node_6, () => get(run).runId, ($$anchor) => {
			var fragment_4 = root_3();
			var node_7 = first_child(fragment_4);
			AgentWindow(node_7, {
				get runId() {
					return get(run).runId;
				},
				get sessionId() {
					return get(run).sessionId;
				},
				get agent() {
					return $$props.agent;
				},
				get server() {
					return $$props.server;
				},
				onstate: (s) => {
					set(runState, s, true);
					if ([
						"done",
						"stopped",
						"error"
					].includes(s)) set(refreshKey, get(refreshKey) + 1);
				}
			});
			var node_8 = sibling(node_7, 4);
			ResultsTable(node_8, {
				get runId() {
					return get(run).runId;
				},
				get server() {
					return $$props.server;
				}
			});
			append($$anchor, fragment_4);
		});
		var node_9 = sibling(node_6, 4);
		each(node_9, 17, () => get(reviews), (r) => r.path, ($$anchor, r) => {
			var div_6 = root_6();
			var div_7 = child(div_6);
			var text_10 = only_child(div_7);
			var node_10 = sibling(div_7, 2);
			var consequent_5 = ($$anchor) => {
				var pre = root_4();
				var text_11 = only_child(pre, true);
				template_effect(() => set_text(text_11, get(reviewText)[get(r).path]));
				append($$anchor, pre);
			};
			var alternate_1 = ($$anchor) => {
				var button_1 = root_5();
				delegated("click", button_1, () => loadReview(get(r)));
				append($$anchor, button_1);
			};
			if_block(node_10, ($$render) => {
				if (get(reviewText)[get(r).path]) $$render(consequent_5);
				else $$render(alternate_1, -1);
			});
			reset(div_6);
			template_effect(() => set_text(text_10, `Review of ${get(r).case ?? ""}`));
			append($$anchor, div_6);
		});
		var node_11 = sibling(node_9, 2);
		each(node_11, 17, () => get(repaired), (r) => r.path, ($$anchor, r) => {
			const c = user_derived(() => get(compare)[get(r).path]);
			var div_8 = root_14();
			var div_9 = child(div_8);
			var text_12 = only_child(div_9);
			var div_10 = sibling(div_9, 2);
			var text_13 = only_child(div_10);
			var node_12 = sibling(div_10, 2);
			var consequent_6 = ($$anchor) => {
				var button_2 = root_7();
				delegated("click", button_2, () => loadCompare(get(r)));
				append($$anchor, button_2);
			};
			var consequent_7 = ($$anchor) => {
				var span_5 = root_8();
				append($$anchor, span_5);
			};
			var alternate_3 = ($$anchor) => {
				var fragment_5 = root_13();
				var node_13 = first_child(fragment_5);
				var consequent_8 = ($$anchor) => {
					var div_11 = root_9();
					var text_14 = only_child(div_11, true);
					template_effect(() => set_text(text_14, get(c).error));
					append($$anchor, div_11);
				};
				if_block(node_13, ($$render) => {
					if (get(c).error) $$render(consequent_8);
				});
				var node_14 = sibling(node_13, 2);
				var consequent_10 = ($$anchor) => {
					const d = user_derived(() => changed(get(c).original, get(c).code));
					var fragment_6 = root_12();
					var div_12 = first_child(fragment_6);
					var text_15 = only_child(div_12);
					var div_13 = sibling(div_12, 2);
					var pre_1 = child(div_13);
					var text_16 = only_child(pre_1, true);
					var pre_2 = sibling(pre_1);
					var text_17 = only_child(pre_2, true);
					reset(div_13);
					var node_15 = sibling(div_13, 2);
					var consequent_9 = ($$anchor) => {
						var span_6 = root_10();
						append($$anchor, span_6);
					};
					var alternate_2 = ($$anchor) => {
						var button_3 = root_11();
						delegated("click", button_3, () => approve(get(r)));
						append($$anchor, button_3);
					};
					if_block(node_15, ($$render) => {
						if (get(c).saved) $$render(consequent_9);
						else $$render(alternate_2, -1);
					});
					template_effect(() => {
						set_text(text_15, `${get(d).removed ?? ""} line(s) removed, ${get(d).added ?? ""} added.`);
						set_text(text_16, get(c).original);
						set_text(text_17, get(c).code);
					});
					append($$anchor, fragment_6);
				};
				if_block(node_14, ($$render) => {
					if (get(c).code) $$render(consequent_10);
				});
				append($$anchor, fragment_5);
			};
			if_block(node_12, ($$render) => {
				if (!get(c)) $$render(consequent_6);
				else if (get(c).busy) $$render(consequent_7, 1);
				else $$render(alternate_3, -1);
			});
			reset(div_8);
			template_effect(() => {
				set_text(text_12, `Repaired copy of ${get(r).case ?? ""}`);
				set_text(text_13, `${get(r).path ?? ""} — the session's numbered changes are in its work/repairs.md (Logs). Approving overwrites the saved script through the PyTest Creator's save; it then reads as edited outside its units.`);
			});
			append($$anchor, div_8);
		});
		var node_16 = sibling(node_11, 2);
		var consequent_11 = ($$anchor) => {
			var div_14 = root_15();
			append($$anchor, div_14);
		};
		if_block(node_16, ($$render) => {
			if (!get(repaired).length && !get(reviews).length) $$render(consequent_11);
		});
		var div_15 = sibling(node_16, 4);
		var ul = sibling(child(div_15), 2);
		each(ul, 21, () => get(finalizeBlockers), index, ($$anchor, b) => {
			var li = root_16();
			var text_18 = only_child(li, true);
			template_effect(() => set_text(text_18, get(b)));
			append($$anchor, li);
		});
		reset(ul);
		reset(div_15);
		template_effect(() => set_text(text_9, ` The session — ${get(run).runId ?? ""}`));
		append($$anchor, fragment_3);
	};
	if_block(node_5, ($$render) => {
		if (get(run)) $$render(consequent_12);
	});
	var node_17 = sibling(node_5, 4);
	RunsList(node_17, {
		get server() {
			return $$props.server;
		},
		kind: "validation",
		get refreshKey() {
			return get(refreshKey);
		},
		onopen: (id) => {
			set(run, {
				runId: id,
				sessionId: null
			}, true);
			set(markers, [], true);
		}
	});
	reset(div);
	template_effect(() => {
		button.disabled = !get(canLaunch);
		set_text(text_3, get(busy) ? "Launching…" : "Launch Validation");
		classes_1 = set_class(div_4, 1, "tc-status", null, classes_1, { "is-bad": get(status).bad });
		set_text(text_8, get(status).msg);
	});
	delegated("click", button, launch);
	append($$anchor, div);
	pop();
}
delegate(["click"]);
//#endregion
//#region src/vd/main.js
function mountVd(target, opts = {}) {
	const app = mount(VdPage, {
		target,
		props: {
			server: opts.server || httpServer(),
			agent: opts.agent || httpAgent(opts.agentUrl),
			preselect: opts.preselect || null,
			openRun: opts.openRun || null,
			...opts.saveScript ? { saveScript: opts.saveScript } : {},
			...opts.pollMs ? { pollMs: opts.pollMs } : {}
		}
	});
	return { destroy() {
		unmount(app);
	} };
}
//#endregion
export { flushSync, mountVd };
