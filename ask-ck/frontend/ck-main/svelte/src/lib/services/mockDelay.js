// Emulates the latency of a real LLM call so loading states/animations can be designed against
// something — remove once real API calls (with their own real latency) replace the mocks.
export function mockDelay(ms = 2400) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
