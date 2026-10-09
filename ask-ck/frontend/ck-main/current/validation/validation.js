// Validation's page lives with the Test Composer's adapters (they share the agent and the islands'
// run machinery); this module only re-exports its renderer under the page directory's own name.
export { renderVdPanel } from '../test-composer/test-composer.js';
