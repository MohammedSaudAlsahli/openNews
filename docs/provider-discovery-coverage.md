# Agno provider discovery coverage

All 68 installed adapters load successfully. Ready means adapter import and construction with its required configuration, not live account validation. Models are fetched dynamically; no static model ID catalog is used.

Live public GET verification: OpenRouter 458 models; Perplexity Sonar 4; Hugging Face router 128; LiteLLM published 3115. No inference requests or user credentials used. Counts are observations from this development run, not permanent promises.

| Adapter | Strategy | Default source / configuration |
|---|---|---|
| aimlapi | openai-compatible | https://api.aimlapi.com/v1/models |
| anthropic | anthropic | anthropic |
| aws-bedrock | bedrock | bedrock |
| aws-claude | bedrock | bedrock |
| azure-ai-foundry | azure | azure |
| azure-foundry-claude | anthropic-foundry | anthropic-foundry |
| azure-openai | azure | azure |
| azure-openai-responses | azure | azure |
| cerebras | openai-compatible | https://api.cerebras.ai/v1/models |
| cerebras-openai | openai-compatible | https://api.cerebras.ai/v1/models |
| cloudflare | cloudflare | cloudflare |
| cohere | cohere | cohere |
| cometapi | openai-compatible | https://api.cometapi.com/v1/models |
| dashscope | openai-compatible | https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models |
| deepinfra | openai-compatible | https://api.deepinfra.com/v1/openai/models |
| deepseek | openai-compatible | https://api.deepseek.com/models |
| fireworks | openai-compatible | https://api.fireworks.ai/inference/v1/models |
| flexai | openai-compatible | https://api.flex.ai/v1/models |
| google | google | google |
| google-interactions | google | google |
| groq | openai-compatible | https://api.groq.com/openai/v1/models |
| heabsy | openai-compatible | https://api.heabsy.com/v1/models |
| huggingface | huggingface | huggingface |
| ibm | ibm | ibm |
| inception | openai-compatible | https://api.inceptionlabs.ai/v1/models |
| internlm | openai-compatible | https://internlm-chat.intern-ai.org.cn/puyu/api/v1/chat/completions/models |
| langdb | openai-compatible | https://api.us-east-1.langdb.ai/models |
| litellm | litellm-published | litellm-published |
| litellm-openai | openai-compatible | http://0.0.0.0:4000/models |
| llama-cpp | openai-compatible | http://127.0.0.1:8080/v1/models |
| llama-openai | openai-compatible | https://api.llama.com/compat/v1//models |
| llmman | openai-compatible | http://127.0.0.1:17434/v1/models |
| lmstudio | openai-compatible | http://127.0.0.1:1234/v1/models |
| meta | openai-compatible | https://api.llama.com/v1/models |
| minimax | openai-compatible | https://api.minimax.io/v1/models |
| mistral | openai-compatible | https://api.mistral.ai/v1/models |
| moonshot | openai-compatible | https://api.moonshot.ai/v1/models |
| n1n | openai-compatible | https://api.n1n.ai/v1/models |
| nebius | openai-compatible | https://api.tokenfactory.nebius.com/v1//models |
| neosantara | openai-compatible | https://api.neosantara.xyz/v1/models |
| nexus | openai-compatible | http://localhost:8000/llm/v1//models |
| nvidia | openai-compatible | https://integrate.api.nvidia.com/v1/models |
| ollama | ollama | ollama |
| ollama-responses | ollama | ollama |
| open-responses | openai-compatible | openai-compatible |
| openai | openai-compatible | https://api.openai.com/v1/models |
| openai-chat | openai-compatible | https://api.openai.com/v1/models |
| openai-responses | openai-compatible | https://api.openai.com/v1/models |
| openrouter | openai-compatible | https://openrouter.ai/api/v1/models |
| openrouter-responses | openai-compatible | https://openrouter.ai/api/v1/models |
| perplexity | perplexity-published | perplexity-published |
| portkey | openai-compatible | https://api.portkey.ai/v1/models |
| ramp | openai-compatible | https://api.router.com/v1/models |
| requesty | openai-compatible | https://router.requesty.ai/v1/models |
| sambanova | openai-compatible | https://api.sambanova.ai/v1/models |
| siliconflow | openai-compatible | https://api.siliconflow.cn/v1/models |
| synthorai | openai-compatible | https://synthorai.io/v1/models |
| together | openai-compatible | https://api.together.xyz/v1/models |
| tokenlab | openai-compatible | https://api.tokenlab.sh/v1/models |
| trustedrouter | openai-compatible | https://api.trustedrouter.com/v1/models |
| tuning-engines | openai-compatible | https://api.tuningengines.com/v1/models |
| vercel | openai-compatible | https://api.v0.dev/v1//models |
| vertexai-claude | vertex | vertex |
| vllm | openai-compatible | http://127.0.0.1:8000/v1/models |
| xai | openai-compatible | https://api.x.ai/v1/models |
| xai-responses | openai-compatible | https://api.x.ai/v1/models |
| xiaomi | openai-compatible | https://api.xiaomimimo.com/v1/models |
| yapi | openai-compatible | https://api.y-api.bestvirtualgoods.com/v1/models |

## Limits that must remain explicit

- OpenAI-compatible listing is attempted at the pinned adapter base URL or the user-configured API endpoint. Import/constructor success does not prove that each remote provider implements `/models`; capability and authentication failures are shown without fabricated data.
- Cloud listings require account settings. Azure lists actual ARM deployments, requiring subscription/resource group/account and an Azure management token; its inference API key is separate. AWS lists text foundation models and active inference profiles. Google Vertex publisher catalogs and IBM catalogs do not prove account entitlement.
- The Ollama list combines installed models with a live public library page. Published but uninstalled entries are not selectable. If the public library is offline, installed models remain available; the source labels that partial condition.
- Perplexity reads the official published Sonar pricing data object. Changes to that document structure cause an explicit refresh error rather than stale hardcoded IDs.
- Credentials are plaintext JSON in an owner-only 0600 file inside an owner-only 0700 directory as requested by the new runtime contract. They are never put in SQLite, request logs, returned errors, or environment variables. This is local file protection, not encryption.

## Additional public-only sweep

Current unauthenticated GET checks also returned AIMLAPI764, DeepInfra177, Inception3, Nvidia80, Requesty784, SambaNova6, TokenLab387, TrustedRouter665. Authentication-required responses are not inference failures. Vercel’s pinned adapter default `https://api.v0.dev/v1/models` returned404; discovery is explicitly unavailable at that endpoint in this check. Do not describe it as verified model listing. No user credentials were involved.
