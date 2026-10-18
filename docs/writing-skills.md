# Writing skills and natural-language routing

OpenStudio's composer defaults to **Auto**. Ask in Arabic or English; the conversation model chooses the relevant writing guide using the `load_editorial_skill` Agno tool. The catalog is small; full guide text is read only when selected. There is no extra classification-model call and no keyword classifier that treats every mention of a platform as a writing request.

Type `/` to search the menu, or use its `/` button without losing existing text. Arrow keys select, Enter/Tab insert a command, Escape closes the menu. Commands apply to one message. Explicit slash selection overrides the manual output format. A successful send returns the format control to Auto. Explicit manual formats remain available for that one request.

| Command | Purpose |
| --- | --- |
| `/linkedin` | A professional LinkedIn draft in your voice |
| `/x` | Independent X posts |
| `/thread` | Ordered X posts forming a thread, each limited to 280 characters |
| `/youtube` | Scripts, titles, descriptions, thumbnail briefs or video ideas |
| `/shorts` | Short spoken scripts |
| `/summarize` | Explain and summarize retrieved or supplied source content |
| `/research` | Evidence-based research and synthesis |
| `/rewrite` | Revise supplied text, preserving facts and voice |
| `/plan` | Propose a content plan, without scheduling publication |
| `/hooks` | Openings and titles grounded in the content |

Examples: `حوّل الخبر هذا لمنشور لينكدإن` or `Turn that into a thread` should select the appropriate guide automatically. `ما الفرق بين يوتيوب ولينكدإن؟` is a question, not a request to generate posts. The model can still misinterpret ambiguous requests; explicit slash selection is the deterministic override. Selected guides appear in the live activity record.

## Editable instructions

Default guide text: `engine/eis_engine/writing_skills.py` (`GUIDES`). Routing policy: `ROUTING` in that same module. Guide catalog: `CATALOG`.

Loaded guides are initialized once under the workspace's `instructions/skills/<id>.md`, beside `article-summary.md` and `daily-report.md`. Edit them inside Settings → Daily report → View and edit instructions. User edits are loaded on the next invocation and survive application updates. At most three guides are loaded per turn, each bounded to 12,000 characters. Guide IDs are allowlisted; paths and scripts cannot be executed through this interface.

News-derived drafts must cite retrieved article IDs. Original/user-supplied content uses `evidence_basis=original` so a personal LinkedIn post does not require an unrelated RSS article. References that are supplied are still validated before saving.

## Reviewed sources and implementation boundary

Reviewed 2026-10-18. These are independently written, lightweight OpenStudio writing adapters informed by review of the projects below, **not installations of their complete plugins**. No upstream script, credentials, analytics connector, publishing API, or remote installer is executed. The adapters deliberately omit fixed engagement promises and mandatory intake interviews when context already answers the request.

| Source | Reviewed revision / useful capability | Integration boundary |
| --- | --- | --- |
| [sergebulaev/linkedin-skills](https://github.com/sergebulaev/linkedin-skills) | `261240ac5c4da8b4465cbd364d14ce52ffed12ce`; post writing, voice, repurposing, planning | Native drafting guides; upstream Apify and Publora integration is not connected |
| [sergebulaev/x-skills](https://github.com/sergebulaev/x-skills) | `ea61d1d0f8874dd20633d241d52a297d57099483`; posts, threads, hooks, rewriting | Local draft artifacts; no publishing or account analytics |
| [AgriciDaniel/claude-youtube](https://github.com/AgriciDaniel/claude-youtube) | `84c3fa6805200632fadb4fe2795ef265511271c7`; scripts, hooks, thumbnail briefs, strategy | Writing guidance only; not channel analytics access or image generation |
| [Clawdbot summarize listing](https://claudeskills.club/skills/summarize-by-clawdbot) and [steipete/summarize](https://github.com/steipete/summarize) | Source extraction and summary CLI; current upstream documents transcripts and optional media dependencies | Existing OpenStudio article reader remains in use. Universal YouTube/audio transcription and the external CLI are not installed |

### Additional useful candidates found in the requested directories

- [Content Research Writer on SkillsMP](https://skillsmp.com/creators/kunagent/kun/resources-bundled-skills-content-research-writer): evidence, citations, research and drafting. [Source](https://github.com/KunAgent/Kun/tree/master/resources/bundled-skills/content-research-writer).
- [Article Writing on AwesomeSkill](https://awesomeskill.ai/skill/affaan-m-ecc-article-writing): longer articles and newsletters in the user's voice. [Source](https://github.com/affaan-m/everything-claude-code/tree/main/skills/article-writing).
- [Blog Repurpose on AwesomeSkill](https://awesomeskill.ai/skill/agricidaniel-claude-blog-blog-repurpose): convert a researched article into several platform formats. [Source](https://github.com/AgriciDaniel/claude-blog).
- [Summarize on ClaudeSkills](https://claudeskills.club/skills/summarize-by-clawdbot): useful candidate for a future optional video/podcast extraction module. Fetch and review the current upstream dependencies before packaging; directory instructions can lag upstream.

Directory security scores and popularity are discovery aids, not a compatibility audit. These additional candidates are documented recommendations, not silently installed packages. Complete external-skill import, updates and rollback remain separate from this built-in guide catalog.

## Editing inside OpenStudio

Settings → Daily report → View and edit instructions (also available from News summaries) opens the shared instruction editor. Choose any writing skill to view its active guide, save edits or restore defaults. Existing local customizations are preserved; there is no need to open the instructions folder.
