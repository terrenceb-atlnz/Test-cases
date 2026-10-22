<script>
  // @ts-nocheck

  // The home page's admin panel (shown after the logo is clicked enough times): the server's
  // status line, plus confirm-first actions to reset sessions and restart the server.
  import { onMount } from "svelte";
  import Button from "./Button.svelte";
  import ConfirmModal from "./ConfirmModal.svelte";
  import StatusModal from "./StatusModal.svelte";
  import {
    fetchAdminStatus,
    describeAdminStatus,
    resetWorkspaceLlmConfig,
    resetAllSessions,
    restartServer,
  } from "../services/adminService.js";

  let adminStatusText = "Loading status…";

  // The panel is only mounted once admin mode is on, so the status is fetched when it appears.
  onMount(() => {
    fetchAdminStatus().then((data) => {
      adminStatusText = describeAdminStatus(data);
    });
  });

  // Single ConfirmModal/StatusModal pair, reused across admin actions — only one can be
  // open at a time anyway, so per-action instances would just be dead weight.
  let confirmOpen = false;
  let confirmTitle = "";
  let confirmMessage = "";
  let confirmOnConfirm = () => {};

  let statusOpen = false;
  let statusKind = "success";
  let statusTitle = "";
  let statusMessage = "";

  function askConfirm(title, message, onConfirm) {
    confirmTitle = title;
    confirmMessage = message;
    confirmOnConfirm = onConfirm;
    confirmOpen = true;
  }

  function showStatus(kind, title, message) {
    statusKind = kind;
    statusTitle = title;
    statusMessage = message;
    statusOpen = true;
  }

  function handleResetWorkspaceLlmConfig() {
    askConfirm(
      "Reset the workspace LLM config?",
      "The saved provider/login default will be cleared (you can re-apply it on Configure). Cases and corpora are untouched.",
      async () => {
        try {
          const d = await resetWorkspaceLlmConfig();
          showStatus(
            "success",
            "Workspace LLM config reset",
            "Cleared: " + (d.cleared || []).join(", "),
          );
        } catch (e) {
          showStatus("error", "Reset failed", String(e));
        }
      },
    );
  }

  function handleResetAllSessions() {
    askConfirm(
      "Reset ALL sessions?",
      "EVERY case's wizard/pytest progress and the workspace LLM default will be cleared. This does NOT touch corpora (Zephyr/TestLink/ATP) — only your working sessions.",
      async () => {
        try {
          const d = await resetAllSessions();
          showStatus(
            "success",
            "All sessions reset",
            "Cleared: " +
              (d.cleared || []).join(", ") +
              " — reload the page for a clean slate.",
          );
        } catch (e) {
          showStatus("error", "Reset failed", String(e));
        }
      },
    );
  }

  function handleRestartServer() {
    askConfirm(
      "Restart the server?",
      "The app reloads (dev server runs with --reload). The page will briefly lose connection and then reconnect.",
      async () => {
        try {
          await restartServer();
          adminStatusText = "Restarting… reconnecting in a moment.";
          setTimeout(() => window.location.reload(), 2500);
        } catch (e) {
          showStatus("error", "Restart failed", String(e));
        }
      },
    );
  }
</script>

<ConfirmModal
  bind:open={confirmOpen}
  title={confirmTitle}
  message={confirmMessage}
  onConfirm={confirmOnConfirm}
/>

<StatusModal
  bind:open={statusOpen}
  status={statusKind}
  title={statusTitle}
  message={statusMessage}
/>

<div class="admin-panel">
  <p class="admin-status">{adminStatusText}</p>

  <div class="admin-section">
    <p class="admin-section-label">Session state</p>
    <div class="admin-actions">
      <Button variant="outline" on:click={handleResetWorkspaceLlmConfig}
        >Reset workspace LLM config</Button
      >
      <Button variant="outline" on:click={handleResetAllSessions}
        >Reset ALL sessions</Button
      >
    </div>
  </div>

  <div class="admin-section">
    <p class="admin-section-label">Server</p>
    <div class="admin-actions">
      <Button variant="outline" on:click={handleRestartServer}
        >Restart server (reload)</Button
      >
    </div>
  </div>
</div>

<style>
  .admin-panel {
    display: flex;
    flex-direction: column;
    gap: 28px;
    margin: 20px auto;
    padding: 24px;
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background-color: var(--color-bg-surface);
  }

  .admin-status {
    margin: 0;
    font-size: 0.9rem;
    color: var(--color-text-muted);
  }

  .admin-section-label {
    margin: 0 0 8px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .admin-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
</style>
