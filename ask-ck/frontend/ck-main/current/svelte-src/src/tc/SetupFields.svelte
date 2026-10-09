<script>
  // Where the run happens — /test-mode's §1 setup answers, collected BEFORE launch and carried in the
  // hand-off (PLAN-agent-sessions D2: nothing can ask mid-run until W2). Pre-filled from this seat's
  // last answers and confirmed every launch.
  let { setup = $bindable() } = $props();
</script>

<div class="tc-fields">
  <div class="tc-field"><label for="tc-testbox">Test bench</label>
    <input id="tc-testbox" class="form-input" placeholder="tb470" bind:value={setup.testbox}></div>
  <div class="tc-field tc-wide"><label for="tc-consoles">Consoles this run may use</label>
    <input id="tc-consoles" class="form-input" placeholder="u0-u5 (u0 = x230 DUT; …)" bind:value={setup.consoles}></div>
  <div class="tc-field"><label for="tc-pdu">PDU IP (blank = no PDU)</label>
    <input id="tc-pdu" class="form-input" placeholder="10.36.150.14" bind:value={setup.pduIp}></div>
  <div class="tc-field tc-wide"><label for="tc-outlets">PDU outlets</label>
    <input id="tc-outlets" class="form-input" placeholder="u0=1, u1=7, u2=6" bind:value={setup.outlets}></div>
  <div class="tc-field tc-full"><label for="tc-constraints">Session constraints (verbatim to the session)</label>
    <input id="tc-constraints" class="form-input" placeholder="e.g. shared box: read-only probe; no reloads before 17:00" bind:value={setup.constraints}></div>
  <div class="tc-field tc-wide"><label for="tc-email">Email when done / on a notice</label>
    <input id="tc-email" class="form-input" placeholder="first.last@alliedtelesis.co.nz" bind:value={setup.email}></div>
</div>
