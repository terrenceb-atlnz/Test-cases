// TODO: replace with real case-lookup / export API calls

const openPartialCases = [
  { id: 'AWPTCM-T44318', label: 'WPTCM-T44318 — (315) AdvancedManagement_AMF - AMF Master support' },
  { id: 'AWPTCM-T44201', label: 'WPTCM-T44201 — (212) VLAN_Configuration - Tagged port assignment' },
  { id: 'AWPTCM-T44087', label: 'WPTCM-T44087 — (108) StaticRouting - Default route fallback' }
];

const completeCases = [
  { id: 'AWPTCM-T43991', label: 'WPTCM-T43991 — (301) LACP_Bonding - Active-active failover' },
  { id: 'AWPTCM-T43876', label: 'WPTCM-T43876 — (150) DHCP_Snooping - Trusted port enforcement' }
];

export function listOpenPartialCases() {
  return openPartialCases;
}

export function listCompleteCases() {
  return completeCases;
}

export function findCase(caseId) {
  return [...openPartialCases, ...completeCases].find((c) => c.id === caseId) ?? null;
}

export function exportSession() {
  // TODO: wire up real export
}
