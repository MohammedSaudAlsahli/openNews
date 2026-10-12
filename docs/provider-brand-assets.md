# Provider brand assets

The app includes friendly names for all 68 pinned Agno adapters plus the OpenAI ChatGPT connection. API variants share their provider’s authentic mark and have distinct names. Images are bundled and loaded offline; provider configuration never triggers a CDN or favicon request.

## Sources and licenses

- models.dev: https://github.com/anomalyco/models.dev — provider logos from its pinned repository tree, MIT. Exact commit URLs are recorded per adapter in `provider-brands.json`.
- Lobe Icons: https://github.com/lobehub/lobe-icons — CometAPI, InternLM, SambaNova and vLLM marks, MIT. Exact commit URLs are recorded in the same manifest.
- Both complete MIT license notices are included beside the bundled assets as `models.dev-LICENSE.txt` and `lobe-icons-LICENSE.txt`.

Original SVGs are retained. PNGs are derived locally at 128×128 for native AppKit loading. `currentColor` is resolved for rasterization, and luminance is converted into an alpha mask so white logo cutouts remain transparent; The initial monochrome catalog marks use native templates for light/dark contrast. Additional official favicons retain their original colors. Brand marks are never mirrored in RTL. Names and marks identify their respective owners; the project does not claim affiliation or trademark ownership.

## OpenWork reference

Reviewed the official implementation at https://github.com/different-ai/openwork/blob/dev/packages/ui/src/react/provider-logo-src.ts and https://github.com/different-ai/openwork/blob/dev/packages/ui/src/react/provider-icon.tsx. It uses known brand marks, Simple Icons/favicons and a monogram fallback. No OpenWork code or logo artwork was copied; this native implementation uses offline licensed assets.

## Coverage

69 of 69 entries have an authentic mark: all 68 Agno adapters and the OpenAI ChatGPT connection. API variants share the corresponding vendor mark. The defensive monogram remains only for future unknown providers or a corrupt/missing resource; no current entry depends on it.

Additional marks were obtained directly from vendor websites (including the CDN URLs explicitly linked in their HTML), official GitHub organization artwork, and the official llama.cpp brand repository. These website/favicon marks are identified as official trademark assets, **not** mislabeled as MIT. They are used solely to identify the configured provider and do not imply affiliation. Exact URLs, official homepages, and PNG SHA-256 hashes are recorded in the manifest.

llama.cpp's assets use CC BY-NC 4.0 plus an explicit brand-usage grant allowing commercial software redistribution for identification. Both the license and grant are bundled. Source: https://github.com/ggml-org/llama.brand; no mark shape was redrawn. LLMMan uses its official GitHub organization's published artwork: https://github.com/llmmanorg. Open Responses uses its official site's favicon: https://www.openresponses.org/svg/favicon.svg.

## Additional official sources

- AI/ML API: https://cdn.prod.website-files.com/65b8f36fa600366bc7cf9a67/68823171a2a0e523e03b0752_Logo%20Icon.png
- FlexAI: https://flex.ai/favicon.ico
- Heabsy: https://heabsy.com/favicon/favicon-96x96.png
- LangDB: https://langdb.ai/favicon.ico
- LiteLLM: https://cdn.prod.website-files.com/69eb241da3f923869c226875/6abea43c7b43e2bc4b306584_litellm_favicon_light_32.png
- LiteLLM · OpenAI API: https://cdn.prod.website-files.com/69eb241da3f923869c226875/6abea43c7b43e2bc4b306584_litellm_favicon_light_32.png
- llama.cpp: https://raw.githubusercontent.com/ggml-org/llama.brand/master/icon/icon-light.svg
- LLMMan: https://avatars.githubusercontent.com/u/316802122?v=4
- N1N: https://n1n.ai/favicon.svg
- Neosantara: https://www.neosantara.xyz/favicon.ico
- Nexus: https://nexusrouter.com/icon.svg
- Open Responses: https://www.openresponses.org/svg/favicon.svg
- Portkey: https://framerusercontent.com/images/pkFK3AGXHirogqiN67JGtlnMVM.png
- Ramp: https://router.com/favicon.ico?favicon.3948ndr73xvax.ico
- Requesty: https://www.requesty.ai/favicon.ico?favicon.2-1x21bz7uom-.ico
- SynthorAI: https://synthorai.io/favicon.svg
- TokenLab: https://tokenlab.sh/favicon.ico?f0a5e9c08248b5d9
- Tuning Engines: https://www.tuningengines.com/favicon.ico
- YAPI: https://y-api.bestvirtualgoods.com/favicon-32.png
