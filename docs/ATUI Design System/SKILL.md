---
name: atui-design
description: Use this skill to generate well-branded interfaces and assets for Allied Telesis ATUI (OneConnect and other Allied Telesis network-management products), either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the readme.md file within this skill, and explore the other available files.
If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.
If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

Key files: `styles.css` (tokens + fonts), `components/**` (React recreations of every `at-*` family), `ui_kits/oneconnect/` (full app shell), `readme.md` (content + visual rules). Upstream source: https://github.com/alliedtelesis-labs-nz/atui-components — prefer the real `@alliedtelesis-labs-nz/atui-components-stencil` components in production.
