/* Built from ask-ck/frontend/ck-main/current/svelte-src/ — do not edit; run `npm run build` there.
* source-sha256:558a27cb0e3e7aa1b1567b09b7d7b588b1938ff9641a2727f4bfacbd57d0518c */
import { B as proxy, C as unmount, E as from_html, G as pop, H as state, I as child, J as reset, K as push, L as first_child, N as template_effect, O as delegate, R as only_child, S as set_text, T as comment, U as flushSync, V as set, W as user_derived, _ as each, a as bind_checked, b as if_block, c as remove_input_defaults, d as bind_select_value, f as init_select, h as set_class, j as get, k as delegated, l as set_attribute, n as onMount, o as bind_group, q as next, r as prop, s as bind_value, u as set_checked, v as index, w as append, x as mount, y as key, z as sibling } from "./disclose-version-Cf35PRTc.js";
import { _ as saveSetup, a as TC_API, c as effectiveVerdict, d as formatOutlets, f as httpAgent, g as runBody, h as parseOutlets, i as AgentWindow, l as fmtDuration, m as loadSetup, n as RunsList, o as VERDICT_ORDER, p as httpServer, r as ResultsTable, s as byCycle, t as SetupFields, u as fmtTokens, v as tokensOf, y as verdictCounts } from "./SetupFields-CxWRVO5r.js";
//#region src/tc/TcTree.svelte
var root$1 = from_html(`<div class="zt-empty">No plans loaded.</div>`);
var root_1$1 = from_html(`<span class="tc-prev">Previously Run</span>`);
var root_2$1 = from_html(`<span class="zt-count">not runnable on this template</span>`);
var root_3$1 = from_html(`<div style="--zt-depth:2"><span class="zt-fold-pad"></span> <label><input type="checkbox"/> <span class="zt-key"> </span> <span> </span> <!> <!></label></div>`);
var root_4$1 = from_html(`<div class="zt-row zt-cycle" style="--zt-depth:1"><button type="button" class="zt-fold"> </button> <label><input type="checkbox"/> <span class="zt-key"> </span> <span class="zt-count"> </span></label></div> <!>`, 1);
var root_5$1 = from_html(`<div class="zt-row zt-plan" style="--zt-depth:0"><span class="zt-key"> </span> </div> <!>`, 1);
var root_6$1 = from_html(`<!> <!>`, 1);
function TcTree($$anchor, $$props) {
	push($$props, true);
	let ticked = prop($$props, "ticked", 15), runnableOnly = prop($$props, "runnableOnly", 3, true);
	let folded = state(proxy({}));
	const plans = user_derived(() => $$props.tree && $$props.tree.plans || []);
	function shown(c) {
		return !runnableOnly() || $$props.runnable(c.key);
	}
	function toggle(key, on) {
		const t = new Set(ticked());
		if (on) t.add(key);
		else t.delete(key);
		ticked(t);
	}
	function toggleCycle(cy, on) {
		const t = new Set(ticked());
		for (const c of cy.cases) if (shown(c) && $$props.runnable(c.key)) {
			if (on) t.add(`${cy.key}/${c.key}`);
			else t.delete(`${cy.key}/${c.key}`);
		}
		ticked(t);
	}
	var fragment = root_6$1();
	var node = first_child(fragment);
	var consequent = ($$anchor) => {
		var div = root$1();
		append($$anchor, div);
	};
	if_block(node, ($$render) => {
		if (!get(plans).length) $$render(consequent);
	});
	var node_1 = sibling(node, 2);
	each(node_1, 17, () => get(plans), (p) => p.key, ($$anchor, p) => {
		var fragment_1 = root_5$1();
		var div_1 = first_child(fragment_1);
		var span = child(div_1);
		var text = only_child(span, true);
		var text_1 = sibling(span);
		reset(div_1);
		var node_2 = sibling(div_1, 2);
		each(node_2, 17, () => get(p).cycles, (cy) => cy.key, ($$anchor, cy) => {
			const vis = user_derived(() => get(cy).cases.filter(shown));
			var fragment_2 = root_4$1();
			var div_2 = first_child(fragment_2);
			var button = child(div_2);
			var text_2 = only_child(button, true);
			var label = sibling(button, 2);
			var input = child(label);
			remove_input_defaults(input);
			var span_1 = sibling(input, 2);
			var text_3 = only_child(span_1, true);
			var text_4 = sibling(span_1);
			var span_2 = sibling(text_4);
			var text_5 = only_child(span_2);
			reset(label);
			reset(div_2);
			var node_3 = sibling(div_2, 2);
			var consequent_3 = ($$anchor) => {
				var fragment_3 = comment();
				var node_4 = first_child(fragment_3);
				each(node_4, 17, () => get(vis), (c) => c.key, ($$anchor, c) => {
					const id = user_derived(() => `${get(cy).key}/${get(c).key}`);
					const ok = user_derived(() => $$props.runnable(get(c).key));
					var div_3 = root_3$1();
					let classes;
					var label_1 = sibling(child(div_3), 2);
					var input_1 = child(label_1);
					remove_input_defaults(input_1);
					var span_3 = sibling(input_1, 2);
					var text_6 = only_child(span_3, true);
					var text_7 = sibling(span_3);
					var span_4 = sibling(text_7);
					var text_8 = only_child(span_4, true);
					var node_5 = sibling(span_4, 2);
					var consequent_1 = ($$anchor) => {
						var span_5 = root_1$1();
						template_effect(($0) => set_attribute(span_5, "title", $0), [() => $$props.previously(get(c).key)]);
						append($$anchor, span_5);
					};
					var d = user_derived(() => $$props.previously(get(c).key));
					if_block(node_5, ($$render) => {
						if (get(d)) $$render(consequent_1);
					});
					var node_6 = sibling(node_5, 2);
					var consequent_2 = ($$anchor) => {
						var span_6 = root_2$1();
						append($$anchor, span_6);
					};
					if_block(node_6, ($$render) => {
						if (!get(ok)) $$render(consequent_2);
					});
					reset(label_1);
					reset(div_3);
					template_effect(($0, $1, $2, $3) => {
						classes = set_class(div_3, 1, "zt-row zt-case", null, classes, { "is-off": $0 });
						input_1.disabled = !get(ok);
						set_checked(input_1, $1);
						set_text(text_6, get(c).key);
						set_text(text_7, ` ${(get(c).name || "") ?? ""} `);
						set_class(span_4, 1, `tc-kind tc-kind-${$2 ?? ""}`);
						set_text(text_8, $3);
					}, [
						() => !ticked().has(get(id)),
						() => ticked().has(get(id)),
						() => $$props.kindOf(get(c).key),
						() => $$props.kindOf(get(c).key) === "script" ? "PyScript" : "Manual"
					]);
					delegated("change", input_1, (e) => toggle(get(id), e.currentTarget.checked));
					append($$anchor, div_3);
				});
				append($$anchor, fragment_3);
			};
			if_block(node_3, ($$render) => {
				if (!get(folded)[get(cy).key]) $$render(consequent_3);
			});
			template_effect(($0) => {
				set_attribute(button, "aria-expanded", !get(folded)[get(cy).key]);
				set_text(text_2, get(folded)[get(cy).key] ? "▸" : "▾");
				set_checked(input, $0);
				set_text(text_3, get(cy).key);
				set_text(text_4, ` ${(get(cy).name || "") ?? ""} `);
				set_text(text_5, `${get(vis).length ?? ""} of ${get(cy).cases.length ?? ""} shown`);
			}, [() => get(vis).some((c) => ticked().has(`${get(cy).key}/${c.key}`))]);
			delegated("click", button, () => set(folded, {
				...get(folded),
				[get(cy).key]: !get(folded)[get(cy).key]
			}, true));
			delegated("change", input, (e) => toggleCycle(get(cy), e.currentTarget.checked));
			append($$anchor, fragment_2);
		});
		template_effect(() => {
			set_text(text, get(p).key);
			set_text(text_1, ` ${(get(p).name || "") ?? ""}`);
		});
		append($$anchor, fragment_1);
	});
	append($$anchor, fragment);
	pop();
}
delegate(["click", "change"]);
//#endregion
//#region src/tc/TcPage.svelte
var root = from_html(`<option> </option>`);
var root_1 = from_html(`<div class="tc-small">No templated projects yet — upload one with the Zephyr Templating Tool, or use a project link.</div>`);
var root_2 = from_html(`<select id="tc-project" class="form-input"><option>— choose a project uploaded by the Templating Tool —</option><!></select> <!>`, 1);
var root_3 = from_html(`<label class="tc-variant"><input type="checkbox"/> <b> </b> <span class="tc-badge"> </span> <span class="tc-small"> </span> <span class="tc-small"> </span></label>`);
var root_4 = from_html(`<div class="tc-small"> </div> <!>`, 1);
var root_5 = from_html(`<div class="tc-line"><input id="tc-wiki" class="form-input" type="url" placeholder="https://wiki.atlnz.lc/awpwiki/index.php/Project:3171_AT-x230-V2"/> <button type="button" class="btn btn-secondary"> </button></div> <!>`, 1);
var root_6 = from_html(`<span class="tc-small"> </span>`);
var root_7 = from_html(`<span class="tc-check" title="the probe matched the template"> </span>`);
var root_8 = from_html(`<span class="tc-problem"> </span>`);
var root_9 = from_html(`<span class="tc-problem">No probe result — see the notices below.</span>`);
var root_10 = from_html(`<span class="tc-small tc-problem">The bench has not been validated against the template.</span>`);
var root_11 = from_html(`<div class="zt-scroll tc-tree"><!></div>`);
var root_12 = from_html(`<pre class="tc-pre"> </pre>`);
var root_13 = from_html(`<!> <!>`, 1);
var root_14 = from_html(`<div class="tc-step"><span class="tc-step-n">6</span> </div> <!>`, 1);
var root_15 = from_html(`<div class="section tc-page"><div class="section-heading">Test Composer</div> <div class="section-description">Pick a project and the test bench, choose the topology template, check the bench against it, then tick the cases to run. Script cases run their saved PyScript; manual cases are run by the session by hand. Everything runs through your seat's agent.</div> <div class="tc-step"><span class="tc-step-n">1</span> Project</div> <div class="tc-line"><label><input type="radio"/> Templated Project</label> <label><input type="radio"/> Zephyr Project Link</label></div> <!> <div class="tc-step"><span class="tc-step-n">2</span> Test bench and template</div> <!> <div class="tc-line"><select id="tc-template" class="form-input"><option>— topology template —</option><!></select> <!></div> <div class="tc-step"><span class="tc-step-n">3</span> Validate the bench against the template</div> <div class="tc-line"><button type="button" id="tc-validate" class="btn btn-primary">Validate</button> <!> <span class="tc-small"> </span></div> <!> <div class="tc-step"><span class="tc-step-n">4</span> What is in the project</div> <div class="tc-line"><button type="button" id="tc-load-tree" class="btn btn-secondary"> </button> <label class="tc-small"><input type="checkbox"/> </label> <!></div> <!> <div class="tc-step"><span class="tc-step-n">5</span> Start</div> <div class="tc-line"><label class="tc-small">Run after hours from <input type="time" class="form-input tc-time"/></label> <button type="button" class="btn btn-secondary"> </button> <button type="button" class="btn btn-secondary">Copy share link</button> <button type="button" id="tc-start" class="btn btn-primary"> </button></div> <!> <div role="status"> </div> <!> <div class="tc-step">Earlier campaigns</div> <!></div>`);
function TcPage($$anchor, $$props) {
	push($$props, true);
	const binding_group = [];
	let preselect = prop($$props, "preselect", 3, null), openRun = prop($$props, "openRun", 3, null), pollMs = prop($$props, "pollMs", 3, 4e3);
	let source = state("templated");
	let projects = state(proxy([]));
	let projectId = state("");
	let wikiUrl = state("");
	let wiki = state(null);
	let variantPick = state(proxy({}));
	let wikiBusy = state(false);
	let setup = state(proxy(Object.assign({
		testbox: "",
		consoles: "",
		pduIp: "",
		outlets: "",
		constraints: "",
		email: ""
	}, loadSetup())));
	let templates = state(proxy([]));
	let template = state("");
	let scripts = state(proxy([]));
	let validateRun = state(null);
	let validateState = state(null);
	let validateMarkers = state(proxy([]));
	let validateText = state("");
	let tree = state(null);
	let treeBusy = state(false);
	let ticked = state(proxy(/* @__PURE__ */ new Set()));
	let runnableOnly = state(true);
	let previous = state(proxy({}));
	let startAfter = state("");
	let run = state(null);
	let refreshKey = state(0);
	let health = state(null);
	let status = state(proxy({
		msg: "",
		bad: false
	}));
	let dryRun = state(null);
	const project = user_derived(() => get(source) === "templated" ? get(projects).find((p) => p.id === get(projectId)) || null : null);
	const plans = user_derived(() => get(source) === "templated" ? get(project) ? get(project).plans : [] : get(wiki) ? get(wiki).variants.flatMap((v, i) => get(variantPick)[i] ? v.plans.map((p) => p.key) : []) : []);
	const version = user_derived(() => get(project) ? get(project).version : get(wiki) ? (get(wiki).variants.find((v, i) => get(variantPick)[i]) || {}).version || null : null);
	const tmpl = user_derived(() => get(templates).find((t) => t.name === get(template)) || null);
	const scriptByCase = user_derived(() => new Map(get(scripts).filter((s) => s.case_key).map((s) => [s.case_key, s])));
	const sessionsOk = user_derived(() => get(health) && get(health).sessions && get(health).sessions.available);
	const probe = user_derived(() => (get(validateMarkers).find((l) => l.startsWith("PROBE ")) || "").split(/\s+/)[1] || null);
	const validated = user_derived(() => get(probe) === "MATCH");
	const tickedCases = user_derived(() => get(tree) ? get(tree).plans.flatMap((p) => p.cycles.flatMap((cy) => cy.cases.filter((c) => get(ticked).has(`${cy.key}/${c.key}`)).map((c) => ({
		key: c.key,
		cycle: cy.key
	})))) : []);
	function setStatus(msg, bad = false) {
		set(status, {
			msg,
			bad
		}, true);
	}
	function kindOf(key) {
		return get(scriptByCase).has(key) ? "script" : "manual";
	}
	function runnable(key) {
		if (!get(tmpl)) return false;
		return kindOf(key) === "script" ? get(tmpl).runnable_scripts.includes(key) : get(tmpl).manual_cases.includes(key);
	}
	async function loadBasics() {
		try {
			set(projects, (await $$props.server("/projects")).projects, true);
		} catch (e) {
			setStatus("Projects: " + e.message, true);
		}
		try {
			set(scripts, (await $$props.server("/scripts")).scripts, true);
		} catch (_) {}
		try {
			set(templates, (await $$props.server("/templates")).templates, true);
		} catch (e) {
			setStatus("Templates: " + e.message, true);
		}
		try {
			set(health, await $$props.agent.health(), true);
		} catch (e) {
			set(health, { error: e.message }, true);
		}
	}
	async function readWiki() {
		if (!get(wikiUrl).trim()) return;
		set(wikiBusy, true);
		try {
			set(wiki, await $$props.server("/projects/from-wiki", {
				method: "POST",
				body: JSON.stringify({ url: get(wikiUrl).trim() })
			}), true);
			set(variantPick, Object.fromEntries(get(wiki).variants.map((_, i) => [i, get(wiki).variants.length === 1])), true);
			setStatus(get(wiki).variants.length > 1 ? "Several variants share this page — tick the ones this run is for." : "");
		} catch (e) {
			setStatus(e.message, true);
		} finally {
			set(wikiBusy, false);
		}
	}
	async function launch(kind, extra) {
		saveSetup(get(setup));
		const created = await $$props.server("/runs", {
			method: "POST",
			body: JSON.stringify(runBody(kind, get(setup), extra))
		});
		const started = await $$props.agent.start({
			run_id: created.run_id,
			handoff: created.handoff,
			mode: "campaign"
		});
		if (!started.ok) throw new Error(started.error || "the seat agent refused the session");
		return {
			runId: created.run_id,
			sessionId: started.session_id,
			handoff: created.handoff
		};
	}
	async function validate() {
		try {
			set(validateRun, await launch("composer-validate", {
				cases: [],
				template: get(template)
			}), true);
			set(validateMarkers, [], true);
			set(validateText, "");
			set(validateState, "starting");
			setStatus(`Validating ${get(setup).testbox} against ${get(template)}…`);
		} catch (e) {
			setStatus("Validate failed: " + e.message, true);
		}
	}
	async function watchValidate() {
		if (!get(validateRun)) return;
		try {
			const d = await $$props.server(`/runs/${encodeURIComponent(get(validateRun).runId)}/events`);
			set(validateMarkers, d.events.filter((e) => e.kind === "marker").map((e) => e.line), true);
			set(validateText, d.events.filter((e) => e.kind === "text" || e.kind === "result").map((e) => e.text || "").join("\n"), true);
		} catch (_) {}
	}
	async function loadTree() {
		if (!get(plans).length) {
			setStatus("Pick a project (or tick a variant) first.", true);
			return;
		}
		set(treeBusy, true);
		try {
			set(tree, await $$props.server(`/projects/tree?plans=${encodeURIComponent(get(plans).join(","))}`), true);
			const t = /* @__PURE__ */ new Set();
			for (const p of get(tree).plans) for (const cy of p.cycles) for (const c of cy.cases) if (runnable(c.key)) t.add(`${cy.key}/${c.key}`);
			set(ticked, t, true);
			await loadPrevious();
			setStatus(`${t.size} runnable case(s) ticked.`);
		} catch (e) {
			setStatus("Could not read the project from Zephyr: " + e.message, true);
		} finally {
			set(treeBusy, false);
		}
	}
	/** Previously Run: an earlier composer run of the same release version with a result for the case. */
	async function loadPrevious() {
		const out = {};
		try {
			const runs = (await $$props.server("/runs?kind=composer&limit=50")).runs;
			for (const r of runs) {
				const d = await $$props.server(`/runs/${encodeURIComponent(r.run_id)}`);
				const v = d.handoff && d.handoff.project && d.handoff.project.version;
				if (!get(version) || v !== get(version)) continue;
				for (const row of d.table) if (row.verdict && !["PENDING", "NOT TESTED"].includes(row.verdict) && !out[row.case]) out[row.case] = `${r.run_id}: ${row.verdict}`;
			}
		} catch (_) {}
		set(previous, out, true);
	}
	function body() {
		const cases = get(tickedCases).map((c) => {
			const s = get(scriptByCase).get(c.key);
			return s ? {
				key: c.key,
				kind: "script",
				script: s.path,
				cycle: c.cycle
			} : {
				key: c.key,
				kind: "manual",
				cycle: c.cycle
			};
		});
		const proj = get(project) ? {
			id: get(project).id,
			product: get(project).product,
			version: get(project).version,
			plans: get(plans)
		} : get(wiki) ? {
			title: get(wiki).title,
			version: get(version),
			plans: get(plans)
		} : null;
		return {
			cases,
			template: get(template),
			project: proj,
			options: {
				email: (get(setup).email || "").trim() || null,
				start_after: get(startAfter) || null
			}
		};
	}
	async function start() {
		if (!get(tickedCases).length) {
			setStatus("Nothing is ticked.", true);
			return;
		}
		try {
			const b = body();
			if (b.options.start_after) {
				const created = await $$props.server("/runs", {
					method: "POST",
					body: JSON.stringify(runBody("composer", get(setup), b))
				});
				setStatus(`Scheduled ${created.run_id} for ${get(startAfter)} (${created.handoff.start_at}). Your seat agent starts it then — keep this seat on and logged in; no tab is needed. The results arrive in the runs list and by email.`);
				set(refreshKey, get(refreshKey) + 1);
				return;
			}
			const r = await launch("composer", b);
			set(run, {
				runId: r.runId,
				sessionId: r.sessionId
			}, true);
			set(refreshKey, get(refreshKey) + 1);
			setStatus(`Started ${r.runId}: ${get(tickedCases).length} case(s).`);
		} catch (e) {
			setStatus("Start failed: " + e.message, true);
		}
	}
	function shareLink() {
		const u = new URL(window.location.href);
		u.searchParams.set("panel", "composer");
		if (get(project)) u.searchParams.set("project", get(project).id);
		if (get(wikiUrl)) u.searchParams.set("wiki", get(wikiUrl));
		if (get(template)) u.searchParams.set("template", get(template));
		try {
			navigator.clipboard.writeText(u.toString());
			setStatus("Share link copied.");
		} catch (_) {
			setStatus(u.toString());
		}
	}
	onMount(() => {
		loadBasics().then(() => {
			if (openRun()) set(run, {
				runId: openRun(),
				sessionId: null
			}, true);
			if (preselect()) setStatus(`Script ${preselect()} preselected: choose its project and a template, then load the tree.`);
		});
		const t = setInterval(watchValidate, pollMs());
		return () => clearInterval(t);
	});
	var div = root_15();
	var div_1 = sibling(child(div), 6);
	var label = child(div_1);
	var input = child(label);
	remove_input_defaults(input);
	input.value = input.__value = "templated";
	next();
	reset(label);
	var label_1 = sibling(label, 2);
	var input_1 = child(label_1);
	remove_input_defaults(input_1);
	input_1.value = input_1.__value = "wiki";
	next();
	reset(label_1);
	reset(div_1);
	var node = sibling(div_1, 2);
	var consequent_1 = ($$anchor) => {
		var fragment = root_2();
		var select = first_child(fragment);
		var option = child(select);
		option.value = option.__value = "";
		var node_1 = sibling(option);
		each(node_1, 17, () => get(projects), index, ($$anchor, p) => {
			var option_1 = root();
			var text = only_child(option_1);
			var option_1_value = {};
			template_effect(() => {
				set_text(text, `${get(p).product ?? ""} · ${get(p).version ?? ""}${get(p).number ? ` · Project ${get(p).number}` : ""} (${get(p).plans.length ?? ""} plan(s))`);
				if (option_1_value !== (option_1_value = get(p).id)) option_1.value = (option_1.__value = option_1_value) ?? "";
			});
			append($$anchor, option_1);
		});
		reset(select);
		init_select(select);
		var node_2 = sibling(select, 2);
		var consequent = ($$anchor) => {
			var div_2 = root_1();
			append($$anchor, div_2);
		};
		if_block(node_2, ($$render) => {
			if (!get(projects).length) $$render(consequent);
		});
		bind_select_value(select, () => get(projectId), ($$value) => set(projectId, $$value));
		append($$anchor, fragment);
	};
	var alternate = ($$anchor) => {
		var fragment_1 = root_5();
		var div_3 = first_child(fragment_1);
		var input_2 = child(div_3);
		remove_input_defaults(input_2);
		var button = sibling(input_2, 2);
		var text_1 = only_child(button, true);
		reset(div_3);
		var node_3 = sibling(div_3, 2);
		var consequent_2 = ($$anchor) => {
			var fragment_2 = root_4();
			var div_4 = first_child(fragment_2);
			var text_2 = only_child(div_4);
			var node_4 = sibling(div_4, 2);
			each(node_4, 17, () => get(wiki).variants, index, ($$anchor, v, i) => {
				var label_2 = root_3();
				var input_3 = child(label_2);
				remove_input_defaults(input_3);
				var b_1 = sibling(input_3, 2);
				var text_3 = only_child(b_1, true);
				var text_4 = sibling(b_1);
				var span = sibling(text_4);
				var text_5 = only_child(span, true);
				var span_1 = sibling(span, 2);
				var text_6 = only_child(span_1, true);
				var span_2 = sibling(span_1, 2);
				var text_7 = only_child(span_2, true);
				reset(label_2);
				template_effect(($0) => {
					set_text(text_3, get(v).project);
					set_text(text_4, ` · ${get(v).version ?? ""} · `);
					set_text(text_5, get(v).status || "status ?");
					set_text(text_6, get(v).title || "");
					set_text(text_7, $0);
				}, [() => get(v).plans.map((p) => `${p.key}${p.name ? " " + p.name : ""}`).join(" · ") || "no plans found"]);
				bind_checked(input_3, () => get(variantPick)[i], ($$value) => get(variantPick)[i] = $$value);
				append($$anchor, label_2);
			});
			template_effect(() => set_text(text_2, `${get(wiki).title ?? ""}: ${get(wiki).variants.length ?? ""} variant(s) in the Test Results cell.`));
			append($$anchor, fragment_2);
		};
		if_block(node_3, ($$render) => {
			if (get(wiki)) $$render(consequent_2);
		});
		template_effect(() => {
			button.disabled = get(wikiBusy);
			set_text(text_1, get(wikiBusy) ? "Reading…" : "Read Test Results");
		});
		bind_value(input_2, () => get(wikiUrl), ($$value) => set(wikiUrl, $$value));
		delegated("click", button, readWiki);
		append($$anchor, fragment_1);
	};
	if_block(node, ($$render) => {
		if (get(source) === "templated") $$render(consequent_1);
		else $$render(alternate, -1);
	});
	var node_5 = sibling(node, 4);
	SetupFields(node_5, {
		get setup() {
			return get(setup);
		},
		set setup($$value) {
			set(setup, $$value, true);
		}
	});
	var div_5 = sibling(node_5, 2);
	var select_1 = child(div_5);
	var option_2 = child(select_1);
	option_2.value = option_2.__value = "";
	var node_6 = sibling(option_2);
	each(node_6, 17, () => get(templates), index, ($$anchor, t) => {
		var option_3 = root();
		var text_8 = only_child(option_3);
		var option_3_value = {};
		template_effect(() => {
			set_text(text_8, `${get(t).name ?? ""}: ${get(t).runnable_count ?? ""} runnable${get(t).note ? " (empty)" : ""}`);
			if (option_3_value !== (option_3_value = get(t).name)) option_3.value = (option_3.__value = option_3_value) ?? "";
		});
		append($$anchor, option_3);
	});
	reset(select_1);
	init_select(select_1);
	var node_7 = sibling(select_1, 2);
	var consequent_3 = ($$anchor) => {
		var span_3 = root_6();
		var text_9 = only_child(span_3, true);
		template_effect(() => set_text(text_9, get(tmpl).note || `${get(tmpl).runnable_scripts.length} script case(s) and ${get(tmpl).manual_cases.length} manual case(s) can run on ${get(tmpl).setup}.`));
		append($$anchor, span_3);
	};
	if_block(node_7, ($$render) => {
		if (get(tmpl)) $$render(consequent_3);
	});
	reset(div_5);
	var div_6 = sibling(div_5, 4);
	var button_1 = child(div_6);
	var node_8 = sibling(button_1, 2);
	var consequent_4 = ($$anchor) => {
		var span_4 = root_7();
		var text_10 = only_child(span_4);
		template_effect(() => set_text(text_10, `✓ the bench matches ${get(template) ?? ""}`));
		append($$anchor, span_4);
	};
	var consequent_5 = ($$anchor) => {
		var span_5 = root_8();
		var text_11 = only_child(span_5);
		template_effect(() => set_text(text_11, `Probe: ${get(probe) ?? ""} — the differences are in the session's report below.`));
		append($$anchor, span_5);
	};
	var consequent_6 = ($$anchor) => {
		var span_6 = root_9();
		append($$anchor, span_6);
	};
	var d_1 = user_derived(() => get(validateState) && [
		"done",
		"stopped",
		"error"
	].includes(get(validateState)));
	if_block(node_8, ($$render) => {
		if (get(validated)) $$render(consequent_4);
		else if (get(probe)) $$render(consequent_5, 1);
		else if (get(d_1)) $$render(consequent_6, 2);
	});
	var span_7 = sibling(node_8, 2);
	var text_12 = only_child(span_7, true);
	reset(div_6);
	var node_9 = sibling(div_6, 2);
	var consequent_7 = ($$anchor) => {
		var fragment_3 = comment();
		var node_10 = first_child(fragment_3);
		key(node_10, () => get(validateRun).runId, ($$anchor) => {
			AgentWindow($$anchor, {
				get runId() {
					return get(validateRun).runId;
				},
				get sessionId() {
					return get(validateRun).sessionId;
				},
				get agent() {
					return $$props.agent;
				},
				get server() {
					return $$props.server;
				},
				compact: true,
				onstate: (s) => set(validateState, s, true)
			});
		});
		append($$anchor, fragment_3);
	};
	if_block(node_9, ($$render) => {
		if (get(validateRun)) $$render(consequent_7);
	});
	var div_7 = sibling(node_9, 4);
	var button_2 = child(div_7);
	var text_13 = only_child(button_2, true);
	var label_3 = sibling(button_2, 2);
	var input_4 = child(label_3);
	remove_input_defaults(input_4);
	var text_14 = sibling(input_4);
	reset(label_3);
	var node_11 = sibling(label_3, 2);
	var consequent_8 = ($$anchor) => {
		var span_8 = root_10();
		append($$anchor, span_8);
	};
	if_block(node_11, ($$render) => {
		if (!get(validated) && get(tree)) $$render(consequent_8);
	});
	reset(div_7);
	var node_12 = sibling(div_7, 2);
	var consequent_9 = ($$anchor) => {
		var div_8 = root_11();
		TcTree(child(div_8), {
			get tree() {
				return get(tree);
			},
			kindOf,
			runnable,
			previously: (k) => get(previous)[k],
			get runnableOnly() {
				return get(runnableOnly);
			},
			get ticked() {
				return get(ticked);
			},
			set ticked($$value) {
				set(ticked, $$value, true);
			}
		});
		reset(div_8);
		append($$anchor, div_8);
	};
	if_block(node_12, ($$render) => {
		if (get(tree)) $$render(consequent_9);
	});
	var div_9 = sibling(node_12, 4);
	var label_4 = child(div_9);
	var input_5 = sibling(child(label_4));
	remove_input_defaults(input_5);
	reset(label_4);
	var button_3 = sibling(label_4, 2);
	var text_15 = only_child(button_3);
	var button_4 = sibling(button_3, 2);
	var button_5 = sibling(button_4, 2);
	var text_16 = only_child(button_5);
	reset(div_9);
	var node_14 = sibling(div_9, 2);
	var consequent_10 = ($$anchor) => {
		var pre = root_12();
		var text_17 = only_child(pre, true);
		template_effect(() => set_text(text_17, get(dryRun)));
		append($$anchor, pre);
	};
	if_block(node_14, ($$render) => {
		if (get(dryRun)) $$render(consequent_10);
	});
	var div_10 = sibling(node_14, 2);
	let classes;
	var text_18 = only_child(div_10, true);
	var node_15 = sibling(div_10, 2);
	var consequent_11 = ($$anchor) => {
		var fragment_5 = root_14();
		var div_11 = first_child(fragment_5);
		var text_19 = sibling(child(div_11));
		reset(div_11);
		var node_16 = sibling(div_11, 2);
		key(node_16, () => get(run).runId, ($$anchor) => {
			var fragment_6 = root_13();
			var node_17 = first_child(fragment_6);
			AgentWindow(node_17, {
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
					if ([
						"done",
						"stopped",
						"error"
					].includes(s)) set(refreshKey, get(refreshKey) + 1);
				}
			});
			var node_18 = sibling(node_17, 2);
			ResultsTable(node_18, {
				get runId() {
					return get(run).runId;
				},
				get server() {
					return $$props.server;
				}
			});
			append($$anchor, fragment_6);
		});
		template_effect(() => set_text(text_19, ` The campaign — ${get(run).runId ?? ""}`));
		append($$anchor, fragment_5);
	};
	if_block(node_15, ($$render) => {
		if (get(run)) $$render(consequent_11);
	});
	var node_19 = sibling(node_15, 4);
	RunsList(node_19, {
		get server() {
			return $$props.server;
		},
		kind: "composer",
		get refreshKey() {
			return get(refreshKey);
		},
		onopen: (id) => set(run, {
			runId: id,
			sessionId: null
		}, true)
	});
	reset(div);
	template_effect(() => {
		button_1.disabled = !get(template) || !get(setup).testbox || !get(setup).consoles || !get(sessionsOk);
		set_text(text_12, get(health) && !get(sessionsOk) ? get(health).error || get(health).sessions && get(health).sessions.reason || "seat agent too old" : "");
		button_2.disabled = !get(plans).length || !get(template) || get(treeBusy);
		set_text(text_13, get(treeBusy) ? "Reading Zephyr…" : "Load the project");
		set_text(text_14, ` runnable on ${(get(template) || "the template") ?? ""} only`);
		set_text(text_15, `${get(dryRun) ? "Hide" : "Show"} the hand-off`);
		button_5.disabled = !get(tickedCases).length || !get(sessionsOk);
		set_text(text_16, `Start (${get(tickedCases).length ?? ""})`);
		classes = set_class(div_10, 1, "tc-status", null, classes, { "is-bad": get(status).bad });
		set_text(text_18, get(status).msg);
	});
	bind_group(binding_group, [], input, () => get(source), ($$value) => set(source, $$value));
	bind_group(binding_group, [], input_1, () => get(source), ($$value) => set(source, $$value));
	bind_select_value(select_1, () => get(template), ($$value) => set(template, $$value));
	delegated("click", button_1, validate);
	delegated("click", button_2, loadTree);
	bind_checked(input_4, () => get(runnableOnly), ($$value) => set(runnableOnly, $$value));
	bind_value(input_5, () => get(startAfter), ($$value) => set(startAfter, $$value));
	delegated("click", button_3, () => set(dryRun, get(dryRun) ? null : JSON.stringify(runBody("composer", get(setup), body()), null, 2), true));
	delegated("click", button_4, shareLink);
	delegated("click", button_5, start);
	append($$anchor, div);
	pop();
}
delegate(["click"]);
//#endregion
//#region src/tc/main.js
function mountTc(target, opts = {}) {
	const app = mount(TcPage, {
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
export { TC_API, VERDICT_ORDER, byCycle, effectiveVerdict, flushSync, fmtDuration, fmtTokens, formatOutlets, httpAgent, httpServer, loadSetup, mountTc, parseOutlets, runBody, saveSetup, tokensOf, verdictCounts };
