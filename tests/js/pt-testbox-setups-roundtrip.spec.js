// BEHAVIOURAL round-trip for the setups editor — the promise "your setup name is
// never rewritten", driven through real DOM rather than asserted against source.
//
// The companion spec (pt-testbox-setups.spec.js) reads the source and proves the
// code is SHAPED right: it keys by `r.name`, it seeds from `Object.entries`. That
// cannot prove the cycle actually preserves a name, which is the thing that broke
// before — the form wrote every setup under one invented key, silently renaming
// whatever its owner had chosen. So this file renders a stored map, reads it back,
// and compares.
//
// `ptReadSetupRows` / `ptRenderSetupRows` are exported for exactly this: they are
// pure DOM-in/DOM-out with no module state, and the rest of the panel is not.
import { describe, it, expect, beforeEach } from 'vitest';
import {
  ptReadSetupRows,
  ptRenderSetupRows,
} from '../ask-ck/CK-main/CK_server/static/js/pytest.js';
import { mountFromIndex, resetDom } from './helpers/fixture-dom.js';

beforeEach(() => {
  resetDom();
  mountFromIndex('pt-tb-setups');
});

/** What ptSaveProfile builds from the rows, minus the validation branches. */
const toMap = (rows) =>
  Object.fromEntries(rows.filter((r) => r.name && r.path).map((r) => [r.name, r.path]));

describe('render -> read is lossless', () => {
  it("preserves an owner's name verbatim, with no 'default' anywhere", () => {
    const stored = { tb470: '/home/st-art/st-art/configs/tb470.setup' };
    ptRenderSetupRows(Object.entries(stored).map(([name, path]) => ({ name, path })));
    const out = toMap(ptReadSetupRows());
    expect(out).toEqual(stored);
    expect(Object.keys(out)).not.toContain('default');
  });

  it('keeps every entry when several people share one testbox', () => {
    const stored = {
      tb470: '/home/st-art/st-art/configs/tb470.setup',
      'terrenceb-ie520': '/home/terrenceb/ie520-pair.setup',
      'jacob-x230': '/home/jacob/x230.setup',
    };
    ptRenderSetupRows(Object.entries(stored).map(([name, path]) => ({ name, path })));
    const rows = ptReadSetupRows();
    expect(rows).toHaveLength(3);
    expect(toMap(rows)).toEqual(stored);
  });

  it('preserves insertion order, so the Run dropdown does not reshuffle', () => {
    const names = ['zulu', 'alpha', 'mike'];
    ptRenderSetupRows(names.map((n) => ({ name: n, path: `/p/${n}.setup` })));
    expect(ptReadSetupRows().map((r) => r.name)).toEqual(names);
  });

  it('survives a name carrying quotes — the value attribute must not break out', () => {
    const name = `bob's "main" box`;
    ptRenderSetupRows([{ name, path: '/p/x.setup' }]);
    const rows = ptReadSetupRows();
    expect(rows).toHaveLength(1);
    expect(rows[0].name).toBe(name);
  });

  it('trims incidental whitespace rather than storing it in the key', () => {
    ptRenderSetupRows([{ name: '  spaced  ', path: '  /p/x.setup  ' }]);
    expect(ptReadSetupRows()[0]).toEqual({ name: 'spaced', path: '/p/x.setup' });
  });
});

describe('the empty state', () => {
  it('renders a "none stored" line and reads back as no rows', () => {
    ptRenderSetupRows([]);
    expect(ptReadSetupRows()).toEqual([]);
    expect(document.getElementById('pt-tb-setups').textContent).toMatch(/None stored/i);
  });

  it('a testbox with no setups round-trips to an empty map, not to a default', () => {
    ptRenderSetupRows(Object.entries({}).map(([name, path]) => ({ name, path })));
    expect(toMap(ptReadSetupRows())).toEqual({});
  });
});

describe('editing in place', () => {
  it('renaming a row changes only that key', () => {
    ptRenderSetupRows([
      { name: 'tb470', path: '/a.setup' },
      { name: 'mine', path: '/b.setup' },
    ]);
    document.querySelectorAll('.tb-setup-name')[1].value = 'terrenceb-ie520';
    expect(toMap(ptReadSetupRows())).toEqual({
      tb470: '/a.setup',
      'terrenceb-ie520': '/b.setup',
    });
  });

  it('a re-render after a typed edit keeps the typed value, not the seeded one', () => {
    ptRenderSetupRows([{ name: 'tb470', path: '/a.setup' }]);
    document.querySelector('.tb-setup-path').value = '/edited.setup';
    // what ptAddSetupRow does: read current DOM, append, re-render
    ptRenderSetupRows(ptReadSetupRows().concat([{ name: '', path: '' }]));
    const rows = ptReadSetupRows();
    expect(rows[0]).toEqual({ name: 'tb470', path: '/edited.setup' });
    expect(rows[1]).toEqual({ name: '', path: '' });
  });

  it('removing a row drops only that one and keeps neighbours intact', () => {
    ptRenderSetupRows([
      { name: 'a', path: '/a.setup' },
      { name: 'b', path: '/b.setup' },
      { name: 'c', path: '/c.setup' },
    ]);
    const rows = ptReadSetupRows();
    rows.splice(1, 1); // what ptRemoveSetupRow does
    ptRenderSetupRows(rows);
    expect(toMap(ptReadSetupRows())).toEqual({ a: '/a.setup', c: '/c.setup' });
  });
});
