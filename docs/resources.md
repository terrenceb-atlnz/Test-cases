# Source System Links

**For overall project framing and purpose**, see [README.md](README.md).

API Docs: https://support.smartbear.com/zephyr-scale-cloud/api-docs/

Old Test Cases: https://testlink.atlnz.lc/index.php

New Test Cases: https://jira.atlnz.lc/secure/Tests.jspa#/v2/testCases

ART Test Cases: https://intranet.atlnz.lc/systest/ATPyLib/regression/indexv1.php?type=0

These links support the Test-cases project, whose goal is to derive Objectives for thin AWPTCM Manual Test Cases and map related Test Suites (many-to-one) using TestLink history and enriched Automated Suites.

# Local LLM Information

Basic usage:

curl -X POST "http://vllm.ai.atlnz.lc/v1/chat/completions" \
  -H "Authorization: Bearer <key-here>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "vllm-fast", // or vllm-thinking
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant."
      },
      {
        "role": "user",
        "content": "Write a short hello world message."
      }
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'

