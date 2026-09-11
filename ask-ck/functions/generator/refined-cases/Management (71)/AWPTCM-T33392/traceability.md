# Traceability & Supporting Data for AWPTCM-T33392 (Management_ManagingConfigurationFilesAndSoftwareVersions - Loading Files using TFTP)

## Primary Decision
- From `data/decisions/dec_02.json`: AWPTCM-T33392 {"m": "AWP-5488", "c": "high", "w": "Exact: TFTP upload/download diff filenames"}
- Zephyr title: "(250) Management_ManagingConfigurationFilesAndSoftwareVersions -  Loading Files using TFTP"
- Folder: /New Platform Test (MASTER)/New Platform Template/Management
- Current Zephyr state: Has initial objective and one step (not thin, but enriching per process).
- Zephyr current objective: "Objective: To test TFTP upload and download using different destination filenames Expected Outcome: TFTP should operate normally in copying and renaming downloaded and uploaded files"

## Top Relevant TestLink Cases
Primary + closely related TFTP cases from the "TFTP" suite. Focus on upload/download with filename handling, compatibility, different storage, error cases.

1. **AWP-5488** (Primary) — TFTP upload and download operation with different destination filename
   - Suite: TFTP
   - Summary: Objective: To test TFTP upload and download using different destination filenames. Expected Outcome: TFTP should operate normally in copying and renaming downloaded and uploaded files.
   - Steps: Execute TFTP copy with Download with different destination filename; Upload with different destination filename. Expect success and destination filename correctly changed.
   - Preconditions: DUT default config with IP to TFTP server, tools TFTP server, PC Console.
   - Justification: Direct high-confidence exact match. Core test for different dest filenames in up/download.

2. **AWP-5497** — TFTP compatibility with AT-TFTP server
   - Suite: TFTP
   - Summary: Objective: To test TFTP compatibility with a server using AT-TFTP Expected Outcome: TFTP should be able to download and upload files.
   - Justification: Compatibility with specific AT-TFTP server (common in environment).

3. **AWP-5478** — TFTP upload
   - Suite: TFTP
   - Summary: [version 3] Edited a step because corresponding to CR41795 issue. Covers TFTP uploads using menu (prompts), start capture.
   - Justification: Basic TFTP upload behavior, related to upload part.

4. **AWP-5485** — TFTP operation with different storage types
   - Suite: TFTP
   - Summary: Objective: To test TFTP behaviour using different storage types Expected Outcome: TFTP should operate without any issue using different storage types (Flash, NVS, Card?).
   - Justification: Storage type handling for TFTP operations.

5. **AWP-5490** — filename does not exist on the switch
   - Suite: TFTP
   - Summary: TFTP upload where file name does not exist on switch.
   - Justification: Error/negative case for non-existent filename.

6. **AWP-5489** — medium becomes full
   - Suite: TFTP
   - Summary: TFTP download where switch medium becomes full: Flash, NVS & Card. Should handle destination/medium becoming full.
   - Justification: Handling full medium/storage errors.

**Tangential Cases Reviewed (summary):** 
- Bootloader TFTP cases (e.g. small packets, TFTPv6) are related but bootloader-specific, not core management TFTP.
- Firewall ALG for TFTP, GRE tunnel TFTP are tangential (networking scenarios).
- OpenFlow file up/download cases low relevance.
- Decision: Focused on core TFTP suite cases for filename, compatibility, storage, errors. Broader file transfer from other areas omitted.

## ATPyLib Cases (Step 3)

**Core TFTP copy:**
- 1345.1001.1 : Copy using tftp - Negative tests. Negative-path validation: wildcard to unreachable, non-existent files to valid server. Fails cleanly with error (no false success or hang). Config unchanged, no exceptions.
- 1331.1001.58947 : Copy run to tftp command would fail if executed via trigger activated script.
- 1331.1001.26725 : After failure "copy backupmember tftp", some files disappear from flash on every stack member (inferred/unsupported in some runs).

**Gaps in ART:** Positive success with different dest filenames, AT-TFTP compat, different storage types (Flash/NVS/Card), full medium handling are primarily from TL. ART focuses on negative/error cases and some script-triggered copies. No strong direct hits for rename/copy with explicit different dest filename success paths.

## Gaps Noted
- Core "different destination filename" success for both upload and download (copy and rename behavior) from TL primary.
- AT-TFTP server compatibility, operation across storage types (Flash, NVS, Card), handling when medium full or file not exist from dedicated TL cases.
- ART provides good negative test coverage (unreachable, non-existent files fail cleanly) and some failure scenarios, but positive filename handling and storage compat rely on TestLink.
- Some ART TFTP cases are UNSUPPORTED or inferred in current runs.

## ART Test Cases String
1345.1001.1 (tftp copy negative tests) + 1331 (copy tftp via triggers, backupmember tftp failures) + related management/file copy cases.

## Tangential Cases Reviewed
- Bootloader-specific TFTP (small packets, TFTPv6) scoped out as not management config file loading.
- Firewall ALG TFTP, GRE tunnel TFTP, OpenFlow file ops are networking scenarios, not core.
- Kept focus on TFTP suite cases for filename/storage/compat.

## Synthesis Notes for Objectives
Zephyr already provides a starting objective and step focused on different dest filenames for up/download and success/rename. We enrich it with artefacts from TL family: successful operation with explicit different dest names on download and upload, compatibility, storage type independence, clean error handling for non-existent file and full medium. Keep declarative artefacts style. Number of bullets flexible.

---
**Status**: TestLink list completed. ATPyLib reviewed. Full artefacts and steps drafted in zephyr_payload.json. Traceability finalized.

Following repeatable workflow in OBJECTIVE_DRAFTING_PROCESS.md.
