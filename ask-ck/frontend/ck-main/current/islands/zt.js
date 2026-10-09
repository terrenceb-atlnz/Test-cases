/* Built from ask-ck/frontend/ck-main/current/svelte-src/ — do not edit; run `npm run build` there.
* source-sha256:558a27cb0e3e7aa1b1567b09b7d7b588b1938ff9641a2727f4bfacbd57d0518c */
import { A as event, B as proxy, C as unmount, D as text, E as from_html, F as $window, G as pop, H as state, I as child, J as reset, K as push, L as first_child, N as template_effect, O as delegate, P as user_effect, R as only_child, S as set_text, T as comment, U as flushSync, V as set, W as user_derived, _ as each, b as if_block, c as remove_input_defaults, g as clsx, h as set_class, i as bind_this, j as get, k as delegated, l as set_attribute, m as set_style, n as onMount, q as next, r as prop, s as bind_value, t as onDestroy, u as set_checked, v as index, w as append, x as mount, z as sibling } from "./disclose-version-Cf35PRTc.js";
//#region src/shared/BusyButton.svelte
var root$6 = from_html(`<span class="ck-spinner" aria-hidden="true"></span><span class="ck-busy-label"> </span>`, 1);
var root_1$6 = from_html(`<button type="button"><!></button>`);
function BusyButton($$anchor, $$props) {
	let id = prop($$props, "id", 3, void 0), cls = prop($$props, "cls", 3, "btn btn-primary"), busyLabel = prop($$props, "busyLabel", 3, "Working…"), busy = prop($$props, "busy", 3, false), flash = prop($$props, "flash", 3, null), disabled = prop($$props, "disabled", 3, false), title = prop($$props, "title", 3, void 0);
	var button = root_1$6();
	let classes;
	var node = child(button);
	var consequent = ($$anchor) => {
		var fragment = root$6();
		var span = sibling(first_child(fragment));
		var text = only_child(span, true);
		template_effect(() => set_text(text, busyLabel()));
		append($$anchor, fragment);
	};
	var alternate = ($$anchor) => {
		var text_1 = text();
		template_effect(() => set_text(text_1, $$props.label));
		append($$anchor, text_1);
	};
	if_block(node, ($$render) => {
		if (busy()) $$render(consequent);
		else $$render(alternate, -1);
	});
	reset(button);
	template_effect(() => {
		set_attribute(button, "id", id());
		classes = set_class(button, 1, clsx(cls()), null, classes, {
			"is-busy": busy(),
			"is-done": flash() === "done",
			"is-error": flash() === "error"
		});
		set_attribute(button, "aria-busy", busy() ? "true" : void 0);
		button.disabled = busy() || disabled();
		set_attribute(button, "title", title());
	});
	delegated("click", button, function(...$$args) {
		$$props.onclick?.apply(this, $$args);
	});
	append($$anchor, button);
}
delegate(["click"]);
//#endregion
//#region src/zt/model.js
var QUESTION_TITLES = {
	Q1: "1. Test plans cut (Test Strategy)",
	Q2: "2. Cycles not relevant",
	Q3: "3. Cases not relevant",
	Q4: "4. Not Mandatory / not Supported on first release (TPS)"
};
/** Every row of the template tree: {id, kind, key, name, parent, depth, item}. */
function treeRows(tree) {
	const rows = [];
	for (const p of tree && tree.plans || []) {
		rows.push({
			id: p.key,
			kind: "plan",
			key: p.key,
			name: p.name,
			parent: null,
			depth: 0,
			item: p
		});
		for (const c of p.cycles || []) {
			const cid = `${p.key}/${c.key}`;
			rows.push({
				id: cid,
				kind: "cycle",
				key: c.key,
				name: c.name,
				parent: p.key,
				depth: 1,
				item: c
			});
			for (const t of c.cases || []) rows.push({
				id: `${cid}/${t.key}`,
				kind: "case",
				key: t.key,
				name: t.name,
				parent: cid,
				depth: 2,
				item: t
			});
		}
	}
	return rows;
}
function descendants(rows, id) {
	return rows.filter((r) => r.id.startsWith(id + "/")).map((r) => r.id);
}
function ancestors(id) {
	const parts = id.split("/");
	const out = [];
	for (let i = 1; i < parts.length; i++) out.push(parts.slice(0, i).join("/"));
	return out;
}
/** Start with everything ticked, then untick what the analysis proposed (and everything below
*  it). Returns {ticked, ai}. A case proposal applies to that case in every cycle of its plan. */
function applyProposals(tree, job) {
	const rows = treeRows(tree);
	const ticked = new Set(rows.map((r) => r.id));
	const ai = /* @__PURE__ */ new Map();
	const plans = job && job.plans || {};
	for (const [planKey, slot] of Object.entries(plans)) for (const d of slot && slot.deselect || []) {
		const hits = rows.filter((r) => r.key === d.key && (r.id === planKey || r.id.startsWith(planKey + "/")));
		for (const r of hits) {
			ai.set(r.id, {
				question: d.question,
				reason: d.reason,
				source: d.source
			});
			ticked.delete(r.id);
			for (const k of descendants(rows, r.id)) ticked.delete(k);
		}
	}
	return {
		ticked,
		ai
	};
}
/** Tick or untick one row: unticking unticks everything below it; ticking ticks everything below
*  it and every row above it (a ticked case needs its cycle and plan). */
function setTick(ticked, tree, id, on) {
	const ids = [id, ...descendants(treeRows(tree), id)];
	if (on) {
		ids.forEach((k) => ticked.add(k));
		ancestors(id).forEach((k) => ticked.add(k));
	} else ids.forEach((k) => ticked.delete(k));
	return ticked;
}
/** The /upload/preview body: the ticked plans, each with ALL its template cycles (an unticked
*  cycle still has to be unlinked from the new plan) marked selected or not, and each selected
*  cycle's unticked cases as `excluded`. */
function uploadSelection(tree, ticked, project) {
	const plans = [];
	for (const p of tree && tree.plans || []) {
		if (!ticked.has(p.key)) continue;
		plans.push({
			key: p.key,
			name: p.name,
			cycles: (p.cycles || []).map((c) => {
				const cid = `${p.key}/${c.key}`;
				return {
					key: c.key,
					name: c.name,
					selected: ticked.has(cid),
					excluded: (c.cases || []).filter((t) => !ticked.has(`${cid}/${t.key}`)).map((t) => t.key)
				};
			})
		});
	}
	return {
		version: project.version || null,
		middle: project.middle || null,
		product: project.product || null,
		number: project.number || null,
		plans
	};
}
/** Is a plan or cycle row open? The user's own fold wins; otherwise it opens only when the
*  analysis unticked something INSIDE it (Terrence 2026-10-07: default-collapsed, "unless a change
*  has been made within them by the LLM analysis"). */
function isOpen(id, ai, folds) {
	if (folds && folds.has(id)) return folds.get(id);
	for (const k of ai.keys()) if (k.startsWith(id + "/")) return true;
	return false;
}
/** The rows on screen: a row shows only when every row above it is open. */
function shownRows(tree, ai, folds) {
	return treeRows(tree).filter((r) => !ancestors(r.id).some((a) => !isOpen(a, ai, folds)));
}
/** "N cycle(s), M case(s), K unticked" for a plan or cycle row; '' for a case. */
function rowCount(tree, row, ticked) {
	if (row.kind === "case") return "";
	const below = treeRows(tree).filter((x) => x.kind === "case" && x.id.startsWith(row.id + "/"));
	const off = below.filter((x) => !ticked.has(x.id)).length;
	return `${row.kind === "plan" ? `${(row.item.cycles || []).length} cycle(s), ` : ""}${below.length} case(s)${off ? `, ${off} unticked` : ""}`;
}
/** "a/b plans · c/d cycles · e/f cases ticked" for the column head. */
function tickSummary(tree, ticked) {
	const rows = treeRows(tree);
	const on = (k) => rows.filter((r) => r.kind === k && ticked.has(r.id)).length;
	const all = (k) => rows.filter((r) => r.kind === k).length;
	return `${on("plan")}/${all("plan")} plans · ${on("cycle")}/${all("cycle")} cycles · ${on("case")}/${all("case")} cases ticked`;
}
function nameOf(tree, key) {
	const r = treeRows(tree).find((x) => x.key === key);
	return r ? r.name || "" : "";
}
/** A field's value, or null when it is blank, `N/A`, `NA`, `None` or `-` (Terrence 2026-10-07:
*  a project may have no team subfolder or no number). */
function cleanField(v) {
	const t = String(v == null ? "" : v).trim();
	return [
		"",
		"n/a",
		"na",
		"none",
		"-"
	].includes(t.toLowerCase()) ? null : t;
}
/** The Results Analysis column's data: the state line, sources, Q1–Q4, gaps, AI Notes and
*  what went wrong (wiki problems, failed plan calls, refused proposals) — shown, never hidden. */
function analysisView(job, tree) {
	if (!job) return null;
	const plans = job.plans || {};
	const slots = Object.values(plans);
	const stateText = {
		reading: "Reading the wiki pages…",
		analysing: `Asking the model: ${slots.filter((s) => [
			"done",
			"error",
			"skipped",
			"stopped"
		].includes(s.state)).length} of ${slots.length} plans answered${job.gaps && job.gaps.state === "done" ? ", gaps done" : ""}…`,
		done: "Analysis complete.",
		cancelled: "Stopped — answers so far are kept.",
		error: "The analysis failed."
	}[job.state] || job.state;
	const pageNames = {
		tps: "TPS",
		strategy: "Test Strategy",
		feature: "Feature Page"
	};
	const sources = job.pages ? Object.entries(job.pages).filter(([, p]) => p).map(([k, p]) => ({
		label: pageNames[k] || k,
		url: p.url,
		title: p.title,
		exists: p.exists
	})) : null;
	const tpsRows = job.tps_rows ? ` TPS feature rows: ${job.tps_rows.sid} SID-style, ${job.tps_rows.prd} PRD-style, ${job.tps_rows.tested} tested.` : "";
	const all = slots.flatMap((s) => s.deselect || []);
	const questions = Object.keys(QUESTION_TITLES).map((q) => ({
		title: QUESTION_TITLES[q],
		items: all.filter((d) => d.question === q).map((d) => ({
			key: d.key,
			name: nameOf(tree, d.key),
			reason: d.reason,
			source: d.source
		}))
	}));
	const g = job.gaps || {};
	const notes = (g.notes || []).map((n) => n.note).concat(Object.entries(plans).flatMap(([pk, s]) => (s.notes || []).map((n) => `${n.key || pk}: ${n.note}`)));
	const problems = (job.wiki_problems || []).slice();
	for (const [pk, s] of Object.entries(plans)) {
		if (s.state === "error") problems.push(`${pk}: the model call failed, so the whole plan stays ticked — ${s.error}`);
		if (s.state === "stopped" || s.state === "skipped") problems.push(`${pk}: stopped before it answered, so the whole plan stays ticked`);
		if ((s.dropped || []).length) problems.push(`${pk}: ${s.dropped.length} proposal(s) refused by the guardrail (${s.dropped.map((d) => d.why).join("; ")})`);
	}
	if ((g.dropped || []).length) problems.push(`gaps: ${g.dropped.length} item(s) refused (${g.dropped.map((d) => d.why).join("; ")})`);
	return {
		state: job.state,
		stateText,
		error: job.error || null,
		sources,
		featurePage: job.feature_page || "?",
		tpsRows,
		questions,
		isDone: job.state === "done",
		gaps: {
			state: g.state,
			error: g.error,
			items: g.gaps || []
		},
		notes,
		problems
	};
}
/** The headline of the real upload's progress (GET /upload/run/{id}). */
var RUN_HEADS = {
	running: "Writing to Zephyr…",
	done: "Upload complete.",
	refused: "Refused — nothing was written.",
	stopped: "Stopped at the first failure — nothing after it was written, and nothing was undone.",
	error: "The upload tool failed."
};
//#endregion
//#region src/zt/ZtAnalysis.svelte
var root$5 = from_html(`<div class="zt-empty">Paste a project page URL and press Organize with LLM.</div>`);
var root_1$5 = from_html(`<div class="zt-problem"> </div>`);
var root_2$4 = from_html(`<li> <a target="_blank" rel="noopener"> </a> </li>`);
var root_3$3 = from_html(`<div class="zt-block"><div class="zt-h">Sources</div> <ul></ul> <div class="zt-small"> </div></div>`);
var root_4$2 = from_html(`<li><span class="zt-key"> </span> <span class="zt-source"> </span></li>`);
var root_5$2 = from_html(`<ul></ul>`);
var root_6$1 = from_html(`<div class="zt-small"> </div>`);
var root_7$1 = from_html(`<div class="zt-block"><div class="zt-h"> <span class="zt-count"> </span></div> <!></div>`);
var root_8$1 = from_html(`<li> <span class="zt-source"> </span> </li>`);
var root_9$1 = from_html(`<li> </li>`);
var root_10 = from_html(`<div class="zt-small">…</div>`);
var root_11 = from_html(`<div class="zt-block"><div class="zt-h">Check these <span class="zt-count"> </span></div> <ul></ul></div>`);
var root_12 = from_html(`<div> </div> <!> <!> <!> <div class="zt-block"><div class="zt-h">5. Gaps — required, no template <span class="zt-count"> </span></div> <!> <!></div> <div class="zt-block"><div class="zt-h">6. AI Notes <span class="zt-count"> </span></div> <!></div> <!>`, 1);
function ZtAnalysis($$anchor, $$props) {
	push($$props, true);
	const v = user_derived(() => analysisView($$props.job, $$props.tree));
	var fragment = comment();
	var node = first_child(fragment);
	var consequent = ($$anchor) => {
		var div = root$5();
		append($$anchor, div);
	};
	var alternate_3 = ($$anchor) => {
		var fragment_1 = root_12();
		var div_1 = first_child(fragment_1);
		var text = only_child(div_1, true);
		var node_1 = sibling(div_1, 2);
		var consequent_1 = ($$anchor) => {
			var div_2 = root_1$5();
			var text_1 = only_child(div_2, true);
			template_effect(() => set_text(text_1, get(v).error));
			append($$anchor, div_2);
		};
		if_block(node_1, ($$render) => {
			if (get(v).error) $$render(consequent_1);
		});
		var node_2 = sibling(node_1, 2);
		var consequent_2 = ($$anchor) => {
			var div_3 = root_3$3();
			var ul = sibling(child(div_3), 2);
			each(ul, 21, () => get(v).sources, index, ($$anchor, s) => {
				var li = root_2$4();
				var text_2 = child(li);
				var a = sibling(text_2);
				var text_3 = only_child(a, true);
				var text_4 = sibling(a, 1, true);
				reset(li);
				template_effect(() => {
					set_text(text_2, `${get(s).label ?? ""}: `);
					set_attribute(a, "href", get(s).url);
					set_text(text_3, get(s).title);
					set_text(text_4, get(s).exists ? "" : " (not created)");
				});
				append($$anchor, li);
			});
			reset(ul);
			var div_4 = sibling(ul, 2);
			var text_5 = only_child(div_4);
			reset(div_3);
			template_effect(() => set_text(text_5, `Feature Page: ${get(v).featurePage ?? ""}.${get(v).tpsRows ?? ""}`));
			append($$anchor, div_3);
		};
		if_block(node_2, ($$render) => {
			if (get(v).sources) $$render(consequent_2);
		});
		var node_3 = sibling(node_2, 2);
		each(node_3, 17, () => get(v).questions, index, ($$anchor, q) => {
			var div_5 = root_7$1();
			var div_6 = child(div_5);
			var text_6 = child(div_6);
			var span = sibling(text_6);
			var text_7 = only_child(span, true);
			reset(div_6);
			var node_4 = sibling(div_6, 2);
			var consequent_3 = ($$anchor) => {
				var ul_1 = root_5$2();
				each(ul_1, 21, () => get(q).items, index, ($$anchor, d) => {
					var li_1 = root_4$2();
					var span_1 = child(li_1);
					var text_8 = only_child(span_1, true);
					var text_9 = sibling(span_1);
					var span_2 = sibling(text_9);
					var text_10 = only_child(span_2);
					reset(li_1);
					template_effect(() => {
						set_text(text_8, get(d).key);
						set_text(text_9, ` ${get(d).name ?? ""} — ${get(d).reason ?? ""} `);
						set_text(text_10, `(${get(d).source ?? ""})`);
					});
					append($$anchor, li_1);
				});
				reset(ul_1);
				append($$anchor, ul_1);
			};
			var alternate = ($$anchor) => {
				var div_7 = root_6$1();
				var text_11 = only_child(div_7, true);
				template_effect(() => set_text(text_11, get(v).isDone ? "None." : "…"));
				append($$anchor, div_7);
			};
			if_block(node_4, ($$render) => {
				if (get(q).items.length) $$render(consequent_3);
				else $$render(alternate, -1);
			});
			reset(div_5);
			template_effect(() => {
				set_text(text_6, `${get(q).title ?? ""} `);
				set_text(text_7, get(q).items.length);
			});
			append($$anchor, div_5);
		});
		var div_8 = sibling(node_3, 2);
		var div_9 = child(div_8);
		var span_3 = sibling(child(div_9));
		var text_12 = only_child(span_3, true);
		reset(div_9);
		var node_5 = sibling(div_9, 2);
		var consequent_4 = ($$anchor) => {
			var div_10 = root_1$5();
			var text_13 = only_child(div_10, true);
			template_effect(() => set_text(text_13, get(v).gaps.error));
			append($$anchor, div_10);
		};
		if_block(node_5, ($$render) => {
			if (get(v).gaps.state === "error") $$render(consequent_4);
		});
		var node_6 = sibling(node_5, 2);
		var consequent_5 = ($$anchor) => {
			var ul_2 = root_5$2();
			each(ul_2, 21, () => get(v).gaps.items, index, ($$anchor, x) => {
				var li_2 = root_8$1();
				var text_14 = child(li_2);
				var span_4 = sibling(text_14);
				var text_15 = only_child(span_4);
				var text_16 = sibling(span_4, 1, true);
				reset(li_2);
				template_effect(() => {
					set_text(text_14, `${get(x).requirement ?? ""} `);
					set_text(text_15, `(${get(x).source ?? ""})`);
					set_text(text_16, get(x).why ? " — " + get(x).why : "");
				});
				append($$anchor, li_2);
			});
			reset(ul_2);
			append($$anchor, ul_2);
		};
		var alternate_1 = ($$anchor) => {
			var div_11 = root_6$1();
			var text_17 = only_child(div_11, true);
			template_effect(() => set_text(text_17, get(v).gaps.state === "done" ? "None found." : get(v).gaps.state === "error" ? "" : "…"));
			append($$anchor, div_11);
		};
		if_block(node_6, ($$render) => {
			if (get(v).gaps.items.length) $$render(consequent_5);
			else $$render(alternate_1, -1);
		});
		reset(div_8);
		var div_12 = sibling(div_8, 2);
		var div_13 = child(div_12);
		var span_5 = sibling(child(div_13));
		var text_18 = only_child(span_5, true);
		reset(div_13);
		var node_7 = sibling(div_13, 2);
		var consequent_6 = ($$anchor) => {
			var ul_3 = root_5$2();
			each(ul_3, 21, () => get(v).notes, index, ($$anchor, n) => {
				var li_3 = root_9$1();
				var text_19 = only_child(li_3, true);
				template_effect(() => set_text(text_19, get(n)));
				append($$anchor, li_3);
			});
			reset(ul_3);
			append($$anchor, ul_3);
		};
		var alternate_2 = ($$anchor) => {
			var div_14 = root_10();
			append($$anchor, div_14);
		};
		if_block(node_7, ($$render) => {
			if (get(v).notes.length) $$render(consequent_6);
			else $$render(alternate_2, -1);
		});
		reset(div_12);
		var node_8 = sibling(div_12, 2);
		var consequent_7 = ($$anchor) => {
			var div_15 = root_11();
			var div_16 = child(div_15);
			var span_6 = sibling(child(div_16));
			var text_20 = only_child(span_6, true);
			reset(div_16);
			var ul_4 = sibling(div_16, 2);
			each(ul_4, 21, () => get(v).problems, index, ($$anchor, p) => {
				var li_4 = root_9$1();
				var text_21 = only_child(li_4, true);
				template_effect(() => set_text(text_21, get(p)));
				append($$anchor, li_4);
			});
			reset(ul_4);
			reset(div_15);
			template_effect(() => set_text(text_20, get(v).problems.length));
			append($$anchor, div_15);
		};
		if_block(node_8, ($$render) => {
			if (get(v).problems.length) $$render(consequent_7);
		});
		template_effect(() => {
			set_class(div_1, 1, `zt-state zt-state-${get(v).state ?? ""}`);
			set_text(text, get(v).stateText);
			set_text(text_12, get(v).gaps.items.length);
			set_text(text_18, get(v).notes.length);
		});
		append($$anchor, fragment_1);
	};
	if_block(node, ($$render) => {
		if (!get(v)) $$render(consequent);
		else $$render(alternate_3, -1);
	});
	append($$anchor, fragment);
	pop();
}
//#endregion
//#region src/zt/ZtConfirm.svelte
var root$4 = from_html(`<li> </li>`);
var root_1$4 = from_html(`<div class="zt-problem"> <ul></ul></div>`);
var root_2$3 = from_html(`<div class="update-overlay"><div class="update-dialog zt-confirm" role="alertdialog" aria-modal="true" aria-labelledby="zt-confirm-title"><div class="update-title" id="zt-confirm-title">Write to Zephyr?</div> <div class="update-body"><div class="zt-confirm-what"><b> </b> · AW+ <b> </b></div> <!> <div> </div> <div> </div> <div class="zt-small">If the product or version is wrong, Cancel and correct What Product / What Version above.</div></div> <div class="zt-confirm-actions"><button type="button" class="btn btn-secondary" data-zt-confirm="no">Cancel</button> <button type="button" class="btn btn-primary" data-zt-confirm="yes">Write to Zephyr</button></div></div></div>`);
function ZtConfirm($$anchor, $$props) {
	push($$props, true);
	const t = user_derived(() => $$props.d.targets || {});
	const c = user_derived(() => $$props.d.counts || {});
	const other = user_derived(() => ($$props.d.project_folders || []).filter((f) => f.version !== $$props.sel.version));
	let noBtn = state(void 0);
	user_effect(() => {
		if (get(noBtn)) get(noBtn).focus();
	});
	var div = root_2$3();
	event("keydown", $window, (e) => {
		if (e.key === "Escape") $$props.onanswer(false);
	});
	var div_1 = child(div);
	var div_2 = sibling(child(div_1), 2);
	var div_3 = child(div_2);
	var b = child(div_3);
	var text = only_child(b, true);
	var b_1 = sibling(b, 2);
	var text_1 = only_child(b_1, true);
	reset(div_3);
	var node = sibling(div_3, 2);
	var consequent = ($$anchor) => {
		var div_4 = root_1$4();
		var text_2 = child(div_4);
		var ul = sibling(text_2);
		each(ul, 21, () => get(other), index, ($$anchor, f) => {
			var li = root$4();
			var text_3 = only_child(li);
			template_effect(() => set_text(text_3, `${get(f).kind === "testplan" ? "plans" : "cycles"}: ${get(f).path ?? ""}`));
			append($$anchor, li);
		});
		reset(ul);
		reset(div_4);
		template_effect(() => set_text(text_2, `This project also has folders under another version — is ${($$props.sel.version || "") ?? ""} still right? `));
		append($$anchor, div_4);
	};
	if_block(node, ($$render) => {
		if (get(other).length) $$render(consequent);
	});
	var div_5 = sibling(node, 2);
	var text_4 = only_child(div_5);
	var div_6 = sibling(div_5, 2);
	var text_5 = only_child(div_6);
	next(2);
	reset(div_2);
	var div_7 = sibling(div_2, 2);
	var button = child(div_7);
	bind_this(button, ($$value) => set(noBtn, $$value), () => get(noBtn));
	var button_1 = sibling(button, 2);
	reset(div_7);
	reset(div_1);
	reset(div);
	template_effect(() => {
		set_text(text, $$props.sel.product || "");
		set_text(text_1, $$props.sel.version || "");
		set_text(text_4, `Into ${(get(t).testplan && get(t).testplan.path || "?") ?? ""}`);
		set_text(text_5, `${(get(c).plans || 0) ?? ""} plan(s), ${(get(c).cycles || 0) ?? ""} cycle(s), ${(get(c).writes || 0) ?? ""} writes${get(c).skipped ? ` — ${get(c).skipped} skipped, already there` : ""}.`);
	});
	delegated("click", div, (e) => {
		if (e.target === e.currentTarget) $$props.onanswer(false);
	});
	delegated("click", button, () => $$props.onanswer(false));
	delegated("click", button_1, () => $$props.onanswer(true));
	append($$anchor, div);
	pop();
}
delegate(["click"]);
//#endregion
//#region src/zt/ZtTree.svelte
var root$3 = from_html(`<div class="zt-empty">No templates imported yet — use Refresh templates.</div>`);
var root_1$3 = from_html(`<span class="zt-fold-pad"></span>`);
var root_2$2 = from_html(`<button type="button" class="zt-fold"> </button>`);
var root_3$2 = from_html(`<span class="zt-count"> </span>`);
var root_4$1 = from_html(`<div class="zt-why"><b> </b> <span class="zt-source"> </span></div>`);
var root_5$1 = from_html(`<div><!> <label><input type="checkbox"/> <span class="zt-key"> </span> <!></label> <!></div>`);
function ZtTree($$anchor, $$props) {
	push($$props, true);
	const rows = user_derived(() => shownRows($$props.tree, $$props.ai, $$props.folds));
	var fragment = comment();
	var node = first_child(fragment);
	var consequent = ($$anchor) => {
		var div = root$3();
		append($$anchor, div);
	};
	var alternate_1 = ($$anchor) => {
		var fragment_1 = comment();
		var node_1 = first_child(fragment_1);
		each(node_1, 17, () => get(rows), (r) => r.id, ($$anchor, r) => {
			const on = user_derived(() => $$props.ticked.has(get(r).id));
			const why = user_derived(() => $$props.ai.get(get(r).id));
			const open = user_derived(() => get(r).kind !== "case" && isOpen(get(r).id, $$props.ai, $$props.folds));
			const count = user_derived(() => rowCount($$props.tree, get(r), $$props.ticked));
			var div_1 = root_5$1();
			let classes;
			var node_2 = child(div_1);
			var consequent_1 = ($$anchor) => {
				var span = root_1$3();
				append($$anchor, span);
			};
			var alternate = ($$anchor) => {
				var button = root_2$2();
				var text = only_child(button, true);
				template_effect(() => {
					set_attribute(button, "data-id", get(r).id);
					set_attribute(button, "aria-expanded", get(open));
					set_attribute(button, "aria-label", `${get(open) ? "Collapse" : "Expand"} ${get(r).key ?? ""}`);
					set_text(text, get(open) ? "▾" : "▸");
				});
				delegated("click", button, () => $$props.onfold(get(r).id));
				append($$anchor, button);
			};
			if_block(node_2, ($$render) => {
				if (get(r).kind === "case") $$render(consequent_1);
				else $$render(alternate, -1);
			});
			var label = sibling(node_2, 2);
			var input = child(label);
			remove_input_defaults(input);
			var span_1 = sibling(input, 2);
			var text_1 = only_child(span_1, true);
			var text_2 = sibling(span_1);
			var node_3 = sibling(text_2);
			var consequent_2 = ($$anchor) => {
				var span_2 = root_3$2();
				var text_3 = only_child(span_2, true);
				template_effect(() => set_text(text_3, get(count)));
				append($$anchor, span_2);
			};
			if_block(node_3, ($$render) => {
				if (get(count)) $$render(consequent_2);
			});
			reset(label);
			var node_4 = sibling(label, 2);
			var consequent_3 = ($$anchor) => {
				var div_2 = root_4$1();
				var b = child(div_2);
				var text_4 = only_child(b, true);
				var text_5 = sibling(b);
				var span_3 = sibling(text_5);
				var text_6 = only_child(span_3);
				reset(div_2);
				template_effect(() => {
					set_text(text_4, get(why).question);
					set_text(text_5, ` ${get(why).reason ?? ""} `);
					set_text(text_6, `— ${get(why).source ?? ""}`);
				});
				append($$anchor, div_2);
			};
			if_block(node_4, ($$render) => {
				if (get(why)) $$render(consequent_3);
			});
			reset(div_1);
			template_effect(() => {
				classes = set_class(div_1, 1, `zt-row zt-${get(r).kind ?? ""}`, null, classes, { "is-off": !get(on) });
				set_style(div_1, `--zt-depth:${get(r).depth ?? ""}`);
				set_attribute(input, "data-id", get(r).id);
				set_checked(input, get(on));
				set_text(text_1, get(r).key);
				set_text(text_2, ` ${(get(r).name || "") ?? ""}`);
			});
			delegated("change", input, (e) => $$props.ontoggle(get(r).id, e.currentTarget.checked));
			append($$anchor, div_1);
		});
		append($$anchor, fragment_1);
	};
	if_block(node, ($$render) => {
		if (!get(rows).length) $$render(consequent);
		else $$render(alternate_1, -1);
	});
	append($$anchor, fragment);
	pop();
}
delegate(["click", "change"]);
//#endregion
//#region src/zt/ZtRun.svelte
var root$2 = from_html(`<div class="zt-problem"> </div>`);
var root_1$2 = from_html(`<div class="zt-small"> </div>`);
var root_2$1 = from_html(`<li> </li>`);
var root_3$1 = from_html(`<div> </div> <!> <!> <!> <!> <ol class="zt-steps"></ol>`, 1);
function ZtRun($$anchor, $$props) {
	push($$props, true);
	const res = user_derived(() => $$props.job && $$props.job.result || {});
	const err = user_derived(() => $$props.job && ($$props.job.error || get(res).error));
	var fragment = comment();
	var node = first_child(fragment);
	var consequent_4 = ($$anchor) => {
		var fragment_1 = root_3$1();
		var div = first_child(fragment_1);
		var text = only_child(div, true);
		var node_1 = sibling(div, 2);
		var consequent = ($$anchor) => {
			var div_1 = root$2();
			var text_1 = only_child(div_1, true);
			template_effect(() => set_text(text_1, get(err)));
			append($$anchor, div_1);
		};
		if_block(node_1, ($$render) => {
			if (get(err)) $$render(consequent);
		});
		var node_2 = sibling(node_1, 2);
		var consequent_1 = ($$anchor) => {
			var div_2 = root_1$2();
			var text_2 = only_child(div_2);
			template_effect(() => set_text(text_2, `Stopped in ${get(res).stopped_at ?? ""}.`));
			append($$anchor, div_2);
		};
		if_block(node_2, ($$render) => {
			if (get(res).stopped_at) $$render(consequent_1);
		});
		var node_3 = sibling(node_2, 2);
		var consequent_2 = ($$anchor) => {
			var div_3 = root_1$2();
			var text_3 = only_child(div_3);
			template_effect(($0) => set_text(text_3, `Created in Zephyr: ${$0 ?? ""}.`), [() => get(res).created.map((x) => `${x.kind} ${x.id} (from ${x.from || ""})`).join(", ")]);
			append($$anchor, div_3);
		};
		if_block(node_3, ($$render) => {
			if ((get(res).created || []).length) $$render(consequent_2);
		});
		var node_4 = sibling(node_3, 2);
		var consequent_3 = ($$anchor) => {
			var div_4 = root_1$2();
			var text_4 = only_child(div_4);
			template_effect(($0) => set_text(text_4, `Skipped: ${$0 ?? ""}.`), [() => get(res).skipped.map((x) => x.key).join(", ")]);
			append($$anchor, div_4);
		};
		if_block(node_4, ($$render) => {
			if ((get(res).skipped || []).length) $$render(consequent_3);
		});
		var ol = sibling(node_4, 2);
		each(ol, 21, () => $$props.job.steps || [], index, ($$anchor, x) => {
			var li = root_2$1();
			var text_5 = only_child(li, true);
			template_effect(() => set_text(text_5, get(x).msg || ""));
			append($$anchor, li);
		});
		reset(ol);
		template_effect(() => {
			set_class(div, 1, `zt-state zt-state-${$$props.job.state ?? ""}`);
			set_text(text, RUN_HEADS[$$props.job.state] || $$props.job.state);
		});
		append($$anchor, fragment_1);
	};
	if_block(node, ($$render) => {
		if ($$props.job) $$render(consequent_4);
	});
	append($$anchor, fragment);
	pop();
}
//#endregion
//#region src/zt/ZtUpload.svelte
var root$1 = from_html(`<li> </li>`);
var root_1$1 = from_html(`<ul></ul>`);
var root_2 = from_html(`<div class="zt-small">None found.</div>`);
var root_3 = from_html(`<div class="zt-small zt-problem">Check What Version: if the project slipped a release, the wiki may still name the old one.</div>`);
var root_4 = from_html(`<li><span class="zt-key"> </span> </li>`);
var root_5 = from_html(`<div class="zt-block"><div class="zt-h">Skipped — already in the project folder</div> <ul></ul></div>`);
var root_6 = from_html(`<li class="zt-problem"> </li>`);
var root_7 = from_html(`<tr><td> </td><td> </td><td><code> </code></td><td> </td></tr>`);
var root_8 = from_html(`<div class="zt-block zt-run"><button id="zt-run" type="button" class="btn btn-primary">Write to Zephyr…</button> <span class="zt-small">asks you to confirm the product and version first</span> <div id="zt-run-result"><!></div></div>`);
var root_9 = from_html(`<div class="zt-h">API Upload — what it will do (nothing is written yet)</div> <div class="zt-small"> </div> <div class="zt-block"><div class="zt-h"> </div> <!> <!></div> <!> <!> <table class="table zt-calls"><thead><tr><th>#</th><th>step</th><th>call</th><th>what</th></tr></thead><tbody></tbody></table> <!>`, 1);
function ZtUpload($$anchor, $$props) {
	push($$props, true);
	const t = user_derived(() => $$props.d.targets || {});
	const c = user_derived(() => $$props.d.counts || {});
	const version = user_derived(() => $$props.sel && $$props.sel.version || "");
	const folders = user_derived(() => $$props.d.project_folders || []);
	const other = user_derived(() => get(folders).filter((f) => f.version !== get(version)));
	const canWrite = user_derived(() => !($$props.d.problems || []).length && ($$props.d.calls || []).length && $$props.sel);
	var fragment = root_9();
	var div = sibling(first_child(fragment), 2);
	var text = only_child(div);
	var div_1 = sibling(div, 2);
	var div_2 = child(div_1);
	var text_1 = only_child(div_2);
	var node = sibling(div_2, 2);
	var consequent = ($$anchor) => {
		var ul = root_1$1();
		each(ul, 21, () => get(folders), index, ($$anchor, f) => {
			var li = root$1();
			var text_2 = only_child(li);
			template_effect(() => {
				set_class(li, 1, clsx(get(f).version !== get(version) ? "zt-problem" : ""));
				set_text(text_2, `${get(f).kind === "testplan" ? "plans" : "cycles"}: ${get(f).path ?? ""}${get(f).version !== get(version) ? ` — a different version from What Version (${get(version)})` : ""}`);
			});
			append($$anchor, li);
		});
		reset(ul);
		append($$anchor, ul);
	};
	var alternate = ($$anchor) => {
		var div_3 = root_2();
		append($$anchor, div_3);
	};
	if_block(node, ($$render) => {
		if (get(folders).length) $$render(consequent);
		else $$render(alternate, -1);
	});
	var node_1 = sibling(node, 2);
	var consequent_1 = ($$anchor) => {
		var div_4 = root_3();
		append($$anchor, div_4);
	};
	if_block(node_1, ($$render) => {
		if (get(other).length) $$render(consequent_1);
	});
	reset(div_1);
	var node_2 = sibling(div_1, 2);
	var consequent_2 = ($$anchor) => {
		var div_5 = root_5();
		var ul_1 = sibling(child(div_5), 2);
		each(ul_1, 21, () => $$props.d.duplicates, index, ($$anchor, x) => {
			var li_1 = root_4();
			var span = child(li_1);
			var text_3 = only_child(span, true);
			var text_4 = sibling(span);
			reset(li_1);
			template_effect(() => {
				set_text(text_3, get(x).key);
				set_text(text_4, ` → ${get(x).name ?? ""} exists`);
			});
			append($$anchor, li_1);
		});
		reset(ul_1);
		reset(div_5);
		append($$anchor, div_5);
	};
	if_block(node_2, ($$render) => {
		if (($$props.d.duplicates || []).length) $$render(consequent_2);
	});
	var node_3 = sibling(node_2, 2);
	var consequent_3 = ($$anchor) => {
		var ul_2 = root_1$1();
		each(ul_2, 21, () => $$props.d.problems, index, ($$anchor, p) => {
			var li_2 = root_6();
			var text_5 = only_child(li_2, true);
			template_effect(() => set_text(text_5, get(p)));
			append($$anchor, li_2);
		});
		reset(ul_2);
		append($$anchor, ul_2);
	};
	if_block(node_3, ($$render) => {
		if (($$props.d.problems || []).length) $$render(consequent_3);
	});
	var table = sibling(node_3, 2);
	var tbody = sibling(child(table));
	each(tbody, 21, () => $$props.d.calls || [], index, ($$anchor, x) => {
		var tr = root_7();
		var td = child(tr);
		var text_6 = only_child(td, true);
		var td_1 = sibling(td);
		var text_7 = only_child(td_1, true);
		var td_2 = sibling(td_1);
		var code = child(td_2);
		var text_8 = only_child(code);
		reset(td_2);
		var td_3 = sibling(td_2);
		var text_9 = only_child(td_3, true);
		reset(tr);
		template_effect(() => {
			set_class(tr, 1, clsx(get(x).known ? "" : "zt-unknown"));
			set_text(text_6, get(x).n);
			set_text(text_7, get(x).op);
			set_text(text_8, `${get(x).method ?? ""} ${get(x).path ?? ""}`);
			set_text(text_9, get(x).about);
		});
		append($$anchor, tr);
	});
	reset(tbody);
	reset(table);
	var node_4 = sibling(table, 2);
	var consequent_4 = ($$anchor) => {
		var div_6 = root_8();
		var button = child(div_6);
		var div_7 = sibling(button, 4);
		ZtRun(child(div_7), { get job() {
			return $$props.run;
		} });
		reset(div_7);
		reset(div_6);
		template_effect(() => button.disabled = $$props.runBusy);
		delegated("click", button, function(...$$args) {
			$$props.onrun?.apply(this, $$args);
		});
		append($$anchor, div_6);
	};
	if_block(node_4, ($$render) => {
		if (get(canWrite)) $$render(consequent_4);
	});
	template_effect(() => {
		set_text(text, `Plan folder: ${(get(t).testplan && get(t).testplan.path || "not found") ?? ""} · Cycle folder: ${(get(t).testrun && get(t).testrun.path || "not found") ?? ""} · ${(get(c).plans || 0) ?? ""} plan(s), ${(get(c).cycles || 0) ?? ""} cycle(s), ${(get(c).calls || 0) ?? ""} calls${get(c).skipped ? `, ${get(c).skipped} skipped` : ""}.`);
		set_text(text_1, `Where ${($$props.sel && $$props.sel.product || "the project") ?? ""} has folders in Zephyr`);
	});
	append($$anchor, fragment);
	pop();
}
delegate(["click"]);
//#endregion
//#region src/zt/ZtPage.svelte
var root = from_html(`<button id="zt-cancel" type="button" class="btn btn-secondary"> </button>`);
var root_1 = from_html(`<div class="section"><div class="section-heading">Zephyr Templating Tool</div> <div class="section-description">Paste a project's wiki page. The model reads its Test Strategy, TPS and Feature Page and proposes which template plans, cycles and cases to leave out — every proposal cites its source, and anything it does not mention stays ticked. Review the ticks, Confirm, then API Upload shows exactly what it would send to Zephyr.</div> <div class="zt-line"><input id="zt-url" class="form-input" type="url" placeholder="https://wiki.atlnz.lc/awpwiki/index.php/Project:3296_IE520_Software" aria-label="Project wiki page URL"/> <!> <!></div> <div class="zt-line"><div class="zt-field"><label for="zt-version">What Version (AW+)</label><input id="zt-version" class="form-input" placeholder="filled in by the analysis"/><span id="zt-version-note" class="zt-small"> </span></div> <div class="zt-field"><label for="zt-product">What Product (DUT)</label><input id="zt-product" class="form-input" placeholder="filled in by the analysis"/></div> <div class="zt-field"><label for="zt-middle">What Team Subfolder</label><input id="zt-middle" class="form-input" placeholder="e.g. Tomahawk — blank if none"/></div> <div class="zt-field"><label for="zt-number">What Project Number</label><input id="zt-number" class="form-input" placeholder="e.g. 3001 — blank or N/A if none"/></div></div> <div id="zt-status" role="status"> </div> <div class="zt-cols"><div class="zt-col"><div class="zt-col-head">Results Analysis</div> <div id="zt-analysis" class="zt-scroll"><!></div></div> <div class="zt-col"><div class="zt-col-head"><span>Test Plans / Cycles / Cases</span><span id="zt-tree-count" class="zt-small"> </span></div> <div id="zt-tree" class="zt-scroll"><!></div></div></div> <div class="zt-line zt-small"><span id="zt-templates-info"> </span> <!></div> <div class="zt-actions"><button id="zt-confirm" type="button" class="btn btn-secondary"> </button> <!></div> <div id="zt-upload-result"><!></div></div> <!>`, 1);
function ZtPage($$anchor, $$props) {
	push($$props, true);
	let pollMs = prop($$props, "pollMs", 3, 2e3);
	let tree = state(null);
	let job = state(null);
	let ticked = state(proxy(/* @__PURE__ */ new Set()));
	let ai = state(proxy(/* @__PURE__ */ new Map()));
	let folds = state(proxy(/* @__PURE__ */ new Map()));
	let manual = [];
	let url = state("");
	let fields = proxy({
		version: "",
		product: "",
		middle: "",
		number: ""
	});
	let touched = {
		version: false,
		product: false,
		middle: false,
		number: false
	};
	let versionNote = state("");
	let status = state(proxy({
		msg: "",
		bad: false
	}));
	let confirmed = state(false);
	let previewed = state(null);
	let preview = state(null);
	let run = state(null);
	let asking = state(null);
	let analysing = state(false);
	let analyseId = state(null);
	let cancelling = state(false);
	let uploadBusy = state(false);
	let refreshBusy = state(false);
	let runBusy = state(false);
	let flash = proxy({
		analyse: null,
		upload: null,
		refresh: null
	});
	let poll = null;
	let runPoll = null;
	const templatesInfo = user_derived(() => {
		if (!get(tree)) return "No templates imported yet.";
		const c = get(tree).counts || {};
		return `Templates imported ${String(get(tree).imported_at || "").slice(0, 16).replace("T", " ")} UTC: ${c.plans} plans, ${c.cycles} cycles, ${c.cases} cases.`;
	});
	const treeCount = user_derived(() => get(tree) ? tickSummary(get(tree), get(ticked)) : "");
	function setStatus(msg, bad = false) {
		set(status, {
			msg: msg || "",
			bad: !!bad
		}, true);
	}
	function doFlash(name, ok) {
		flash[name] = ok ? "done" : "error";
		setTimeout(() => {
			flash[name] = null;
		}, 1200);
	}
	/** What the upload targets — all four from the fields, which the analysis fills and the user may
	*  correct (Terrence 2026-10-07: a reload or a stopped analysis no longer loses them). */
	function project() {
		return {
			version: cleanField(fields.version) || "",
			product: cleanField(fields.product) || "",
			middle: cleanField(fields.middle),
			number: cleanField(fields.number)
		};
	}
	function setConfirmed(on) {
		set(confirmed, on, true);
		if (!on && !get(run)) {
			set(previewed, null);
			set(preview, null);
		}
	}
	async function loadTree() {
		const d = await $$props.api("/templates");
		set(tree, d.snapshot, true);
		set(ticked, new Set(treeRows(get(tree)).map((r) => r.id)), true);
		set(ai, /* @__PURE__ */ new Map(), true);
		manual = [];
		set(folds, /* @__PURE__ */ new Map(), true);
	}
	/** The analysis's ticks, then the user's own changes on top (a poll must not undo a click). */
	function rebuildTicks() {
		const f = applyProposals(get(tree), get(job));
		const t = f.ticked;
		for (const [id, on] of manual) setTick(t, get(tree), id, on);
		set(ticked, t, true);
		set(ai, f.ai, true);
	}
	function fillProject(p) {
		if (!p) return;
		for (const k of [
			"version",
			"product",
			"middle",
			"number"
		]) if (!touched[k]) fields[k] = p[k] || "";
		set(versionNote, p.version ? `from the ${p.version_source}${p.project_version ? ` — the project page says ${p.project_version}` : ""}` : "", true);
	}
	function stopPolling() {
		if (poll) {
			clearInterval(poll);
			poll = null;
		}
		set(analyseId, null);
		set(cancelling, false);
	}
	async function pollOnce(id) {
		let d;
		try {
			d = await $$props.api("/analyse/" + encodeURIComponent(id));
		} catch (e) {
			stopPolling();
			set(analysing, false);
			setStatus(e.message, true);
			return;
		}
		set(job, d, true);
		fillProject(d.project);
		rebuildTicks();
		setConfirmed(false);
		if ([
			"done",
			"error",
			"cancelled"
		].includes(d.state)) {
			stopPolling();
			set(analysing, false);
			doFlash("analyse", d.state === "done");
			setStatus(d.state === "done" ? "Review the ticks, then Confirm." : "", d.state === "error");
		}
	}
	async function analyse() {
		const u = get(url).trim();
		if (!u) {
			setStatus("Paste the project page URL first.", true);
			return;
		}
		if (!get(tree)) {
			setStatus("No templates imported yet — Refresh templates first.", true);
			return;
		}
		if (get(analysing)) return;
		set(analysing, true);
		stopPolling();
		manual = [];
		set(folds, /* @__PURE__ */ new Map(), true);
		touched = {
			version: false,
			product: false,
			middle: false,
			number: false
		};
		set(run, null);
		setConfirmed(false);
		setStatus("");
		try {
			const { id } = await $$props.api("/analyse", {
				method: "POST",
				body: JSON.stringify({ url: u })
			});
			set(job, {
				id,
				state: "reading",
				plans: {}
			}, true);
			set(analyseId, id, true);
			poll = setInterval(() => pollOnce(id), pollMs());
		} catch (e) {
			set(analysing, false);
			doFlash("analyse", false);
			setStatus(e.message, true);
		}
	}
	async function cancel() {
		if (!get(analyseId)) return;
		set(cancelling, true);
		try {
			await $$props.api("/analyse/" + encodeURIComponent(get(analyseId)) + "/cancel", { method: "POST" });
			setStatus("Stopping — the calls with the model are being cancelled.");
		} catch (e) {
			setStatus(e.message, true);
			set(cancelling, false);
		}
	}
	function fold(id) {
		const next = new Map(get(folds));
		next.set(id, !isOpen(id, get(ai), get(folds)));
		set(folds, next, true);
	}
	function toggle(id, on) {
		manual.push([id, on]);
		set(ticked, setTick(new Set(get(ticked)), get(tree), id, on), true);
		setConfirmed(false);
	}
	function fieldInput(k) {
		touched[k] = true;
		setConfirmed(false);
	}
	function confirm() {
		if (!get(tree)) return;
		const sel = uploadSelection(get(tree), get(ticked), project());
		if (!sel.plans.length) {
			setStatus("Nothing is ticked.", true);
			return;
		}
		setConfirmed(true);
		setStatus(`Confirmed: ${sel.plans.length} plan(s). API Upload shows what it would do — nothing is written yet.`);
	}
	async function upload() {
		if (!get(confirmed) || get(uploadBusy)) return;
		set(uploadBusy, true);
		let ok = false;
		try {
			const sel = uploadSelection(get(tree), get(ticked), project());
			const d = await $$props.api("/upload/preview", {
				method: "POST",
				body: JSON.stringify(sel)
			});
			set(previewed, sel, true);
			set(preview, d, true);
			set(run, null);
			ok = true;
		} catch (e) {
			setStatus(e.message, true);
		} finally {
			set(uploadBusy, false);
			doFlash("upload", ok);
		}
	}
	function stopRunPolling() {
		if (runPoll) {
			clearInterval(runPoll);
			runPoll = null;
		}
	}
	async function pollRun(id) {
		let d;
		try {
			d = await $$props.api("/upload/run/" + encodeURIComponent(id));
		} catch (e) {
			stopRunPolling();
			setStatus(e.message, true);
			return;
		}
		set(run, d, true);
		if (d.state !== "running") {
			stopRunPolling();
			setStatus(d.state === "done" ? "Upload complete." : "The upload did not complete — see below.", d.state !== "done");
		}
	}
	function askToWrite() {
		return new Promise((resolve) => {
			set(asking, resolve, true);
		});
	}
	function answer(yes) {
		const r = get(asking);
		set(asking, null);
		if (r) r(yes);
	}
	/** The real upload of exactly the selection API Upload listed (§5b). */
	async function writeToZephyr() {
		const sel = get(previewed);
		if (!sel || !get(preview)) return;
		if (!await askToWrite()) return;
		set(runBusy, true);
		try {
			const { id } = await $$props.api("/upload/run", {
				method: "POST",
				body: JSON.stringify(Object.assign({}, sel, {
					confirm_product: sel.product,
					confirm_version: sel.version
				}))
			});
			set(run, {
				id,
				state: "running",
				steps: []
			}, true);
			stopRunPolling();
			runPoll = setInterval(() => pollRun(id), pollMs());
		} catch (e) {
			setStatus(e.message, true);
			set(runBusy, false);
		}
	}
	async function refreshTemplates() {
		if (get(refreshBusy)) return;
		set(refreshBusy, true);
		let ok = false;
		try {
			const d = await $$props.api("/templates/refresh", { method: "POST" });
			await loadTree();
			if (get(job)) rebuildTicks();
			setConfirmed(false);
			setStatus(`Templates refreshed: ${d.written ? d.written.plans + " plans" : "done"}.`);
			ok = true;
		} catch (e) {
			setStatus(e.message, true);
		} finally {
			set(refreshBusy, false);
			doFlash("refresh", ok);
		}
	}
	onMount(async () => {
		try {
			await loadTree();
		} catch (e) {
			setStatus("Could not load the templates: " + e.message, true);
		}
	});
	onDestroy(() => {
		stopPolling();
		stopRunPolling();
	});
	var fragment = root_1();
	var div = first_child(fragment);
	var div_1 = sibling(child(div), 4);
	var input = child(div_1);
	remove_input_defaults(input);
	var node = sibling(input, 2);
	BusyButton(node, {
		id: "zt-analyse",
		label: "Organize with LLM",
		busyLabel: "Organizing…",
		get busy() {
			return get(analysing);
		},
		get flash() {
			return flash.analyse;
		},
		onclick: analyse
	});
	var node_1 = sibling(node, 2);
	var consequent = ($$anchor) => {
		var button = root();
		var text = only_child(button, true);
		template_effect(() => {
			button.disabled = get(cancelling);
			set_text(text, get(cancelling) ? "Stopping…" : "Stop");
		});
		delegated("click", button, cancel);
		append($$anchor, button);
	};
	if_block(node_1, ($$render) => {
		if (get(analyseId)) $$render(consequent);
	});
	reset(div_1);
	var div_2 = sibling(div_1, 2);
	var div_3 = child(div_2);
	var input_1 = sibling(child(div_3));
	remove_input_defaults(input_1);
	var span = sibling(input_1);
	var text_1 = only_child(span, true);
	reset(div_3);
	var div_4 = sibling(div_3, 2);
	var input_2 = sibling(child(div_4));
	remove_input_defaults(input_2);
	reset(div_4);
	var div_5 = sibling(div_4, 2);
	var input_3 = sibling(child(div_5));
	remove_input_defaults(input_3);
	reset(div_5);
	var div_6 = sibling(div_5, 2);
	var input_4 = sibling(child(div_6));
	remove_input_defaults(input_4);
	reset(div_6);
	reset(div_2);
	var div_7 = sibling(div_2, 2);
	let classes;
	var text_2 = only_child(div_7, true);
	var div_8 = sibling(div_7, 2);
	var div_9 = child(div_8);
	var div_10 = sibling(child(div_9), 2);
	ZtAnalysis(child(div_10), {
		get job() {
			return get(job);
		},
		get tree() {
			return get(tree);
		}
	});
	reset(div_10);
	reset(div_9);
	var div_11 = sibling(div_9, 2);
	var div_12 = child(div_11);
	var span_1 = sibling(child(div_12));
	var text_3 = only_child(span_1, true);
	reset(div_12);
	var div_13 = sibling(div_12, 2);
	ZtTree(child(div_13), {
		get tree() {
			return get(tree);
		},
		get ticked() {
			return get(ticked);
		},
		get ai() {
			return get(ai);
		},
		get folds() {
			return get(folds);
		},
		ontoggle: toggle,
		onfold: fold
	});
	reset(div_13);
	reset(div_11);
	reset(div_8);
	var div_14 = sibling(div_8, 2);
	var span_2 = child(div_14);
	var text_4 = only_child(span_2, true);
	BusyButton(sibling(span_2, 2), {
		id: "zt-refresh",
		cls: "btn btn-secondary btn-compact-small",
		label: "Refresh templates",
		busyLabel: "Reading Zephyr…",
		get busy() {
			return get(refreshBusy);
		},
		get flash() {
			return flash.refresh;
		},
		title: "Re-read the template plans, cycles and cases from Zephyr (read only)",
		onclick: refreshTemplates
	});
	reset(div_14);
	var div_15 = sibling(div_14, 2);
	var button_1 = child(div_15);
	var text_5 = only_child(button_1, true);
	var node_5 = sibling(button_1, 2);
	{
		let $0 = user_derived(() => !get(confirmed));
		BusyButton(node_5, {
			id: "zt-upload",
			label: "API Upload",
			busyLabel: "Preparing…",
			get busy() {
				return get(uploadBusy);
			},
			get flash() {
				return flash.upload;
			},
			get disabled() {
				return get($0);
			},
			title: "Lists the calls first — nothing is written until you type the product and version and press Write to Zephyr",
			onclick: upload
		});
	}
	reset(div_15);
	var div_16 = sibling(div_15, 2);
	var node_6 = child(div_16);
	var consequent_1 = ($$anchor) => {
		ZtUpload($$anchor, {
			get d() {
				return get(preview);
			},
			get sel() {
				return get(previewed);
			},
			get run() {
				return get(run);
			},
			get runBusy() {
				return get(runBusy);
			},
			onrun: writeToZephyr
		});
	};
	if_block(node_6, ($$render) => {
		if (get(preview) && get(previewed)) $$render(consequent_1);
	});
	reset(div_16);
	reset(div);
	var node_7 = sibling(div, 2);
	var consequent_2 = ($$anchor) => {
		ZtConfirm($$anchor, {
			get d() {
				return get(preview);
			},
			get sel() {
				return get(previewed);
			},
			onanswer: answer
		});
	};
	if_block(node_7, ($$render) => {
		if (get(asking) && get(preview) && get(previewed)) $$render(consequent_2);
	});
	template_effect(() => {
		set_text(text_1, get(versionNote));
		classes = set_class(div_7, 1, "zt-status", null, classes, { "is-bad": get(status).bad });
		set_text(text_2, get(status).msg);
		set_text(text_3, get(treeCount));
		set_text(text_4, get(templatesInfo));
		set_text(text_5, get(confirmed) ? "Confirmed ✓" : "Confirm");
	});
	bind_value(input, () => get(url), ($$value) => set(url, $$value));
	delegated("input", input_1, () => fieldInput("version"));
	bind_value(input_1, () => fields.version, ($$value) => fields.version = $$value);
	delegated("input", input_2, () => fieldInput("product"));
	bind_value(input_2, () => fields.product, ($$value) => fields.product = $$value);
	delegated("input", input_3, () => fieldInput("middle"));
	bind_value(input_3, () => fields.middle, ($$value) => fields.middle = $$value);
	delegated("input", input_4, () => fieldInput("number"));
	bind_value(input_4, () => fields.number, ($$value) => fields.number = $$value);
	delegated("click", button_1, confirm);
	append($$anchor, fragment);
	pop();
}
delegate(["click", "input"]);
//#endregion
//#region src/zt/main.js
var ZT_API = "/api/zephyr-tool";
/** fetch() against the zephyr-tool router; throws the server's `detail` (string or {error}). */
function httpApi(base = ZT_API) {
	return async function api(path, opts = {}) {
		const r = await fetch(base + path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts));
		const d = await r.json().catch(() => ({}));
		if (!r.ok) {
			const det = d.detail;
			throw new Error(typeof det === "string" ? det : det && det.error ? det.error : `HTTP ${r.status}`);
		}
		return d;
	};
}
function mountZt(target, opts = {}) {
	const app = mount(ZtPage, {
		target,
		props: {
			api: opts.api || httpApi(),
			pollMs: opts.pollMs ?? 2e3
		}
	});
	return { destroy() {
		unmount(app);
	} };
}
//#endregion
export { ZT_API, flushSync, httpApi, mountZt };
