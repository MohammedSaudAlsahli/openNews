// Browser-only behavioral fixture. Never imported by the production entry.
import { mockIPC } from "@tauri-apps/api/mocks";
const params = new URLSearchParams(location.search);
const firstRun = params.has("first");
const activityMode = params.get("activity");
const longNames = params.has("long");
let modelAttempts = 0;
let addedSkills: Record<string, any>[] = [];
const skillRows = [
  [
    "research",
    "بحث موثّق",
    "Research",
    "جمع المصادر ومقارنة الادعاءات",
    "Find sources and compare claims",
  ],
  [
    "rewrite",
    "تحسين الصياغة",
    "Rewrite",
    "تحسين الوضوح والحفاظ على صوتك",
    "Improve clarity while preserving your voice",
  ],
  [
    "linkedin",
    "منشور LinkedIn",
    "LinkedIn post",
    "صياغة منشور مهني بأسلوبك",
    "Write a professional post in your voice",
  ],
  [
    "summarize",
    "شرح وتلخيص",
    "Explain and summarize",
    "شرح المصدر مع تفاصيله وحدوده",
    "Explain sources with detail and limitations",
  ],
  [
    "thread",
    "سلسلة X",
    "X thread",
    "شرح متسلسل بمنشورات مترابطة",
    "Explain a topic in connected posts",
  ],
].map(([id, title_ar, title_en, description_ar, description_en]) => ({
  id,
  title_ar,
  title_en,
  description_ar,
  description_en,
  origin: "builtin",
}));
const localModels = [
  {
    id: "qwen3.5:2b",
    name: "Qwen3.5 · 2B",
    description: "Local article explanations",
    capabilities: ["completion"],
    size: 1.6e9,
  },
];
let localDownload = {
  phase: params.get("download") || "idle",
  model: "qwen3.5:2b",
  completed: 8e8,
  total: 1.6e9,
};
let localPolicy = {
  mode: "quiet",
  index_on_battery: false,
  paused: false,
  phase: "ready",
  thermal: "nominal",
  low_power: false,
  on_battery: false,
  memory_pressure: "normal",
  metrics: {},
};
const qaExecution = {
  elapsed_seconds: 13,
  summary_language: params.get("lang") || "en",
  reasoning_summary:
    params.get("lang") === "ar"
      ? "التخطيط لبحث واسع عن أحدث الأخبار"
      : "Planning a broad search for the latest news",
  steps: [
    { id: "1", kind: "context", detail: "" },
    {
      id: "2",
      kind: "library",
      detail: "أبرز الأخبار التقنية والذكاء الاصطناعي والأعمال اليوم",
    },
    {
      id: "3",
      kind: "web_search",
      detail:
        "latest major news October 24 2026 technology AI business world headlines",
    },
  ],
};
localStorage.setItem("interface-language", params.get("lang") || "en");
localStorage.setItem("theme", params.get("theme") || "light");
localStorage.setItem("welcome-dismissed", firstRun ? "false" : "true");
localStorage.setItem("model-consent", "true");
if (params.has("settings"))
  sessionStorage.setItem(
    "settings-tab",
    params.get("settings") || "appearance",
  );
const now = new Date().toISOString();
const articles = [
  {
    id: "a1",
    title: "لماذا تتخلى شركات التجارة الإلكترونية عن المدفوعات؟",
    source_title: "صفر لواحد",
    summary:
      "لماذا استغنت أمازون ونون عن خدماتها؟ قراءة في دور المدفوعات في التجارة الإلكترونية.",
    url: "https://newsletter.zto.sa/",
    body_status: "full",
    published_at: now,
  },
  {
    id: "a2",
    title:
      "Will it be a golden age or a dark age for mathematics (and science)?",
    source_title: "Hacker News",
    summary:
      "A discussion about the future of mathematical research, scientific tools, and discovery.",
    url: "https://terrytao.wordpress.com/",
    body_status: "full",
    published_at: now,
  },
  {
    id: "a3",
    title: "Building software with a local language model",
    source_title: "Ollama Blog",
    summary:
      "A closer look at local models, memory and the tools that make them useful.",
    url: "https://ollama.com/blog",
    body_status: "full",
    published_at: now,
  },
];
const feeds = [
  {
    id: "s1",
    title: "صفر لواحد",
    url: "https://newsletter.zto.sa/feed",
    feed_url: "https://newsletter.zto.sa/feed",
    enabled: true,
    status: "ready",
    category: "business",
    language: "ar",
    interval_minutes: 5,
    description_ar: "أخبار وتحليلات الأعمال والتقنية والاستثمار في المنطقة.",
    description_en:
      "Business, technology and investment stories from the region.",
  },
  {
    id: "s2",
    title: "Hacker News",
    url: "https://hnrss.org/frontpage",
    enabled: true,
    status: "ready",
    category: "technology",
    language: "en",
    interval_minutes: 5,
    description_en: "Technology stories and discussions from the community.",
  },
  {
    id: "s3",
    title: "Ollama Blog",
    url: "https://ollama.com/blog",
    category: "technology",
    language: "en",
    description_en: "Local models and practical tools for working with AI.",
  },
  {
    id: "s4",
    title: "Epoch AI",
    url: "https://epoch.ai/atom.xml",
    category: "science",
    language: "en",
    description_en:
      "Research on the trajectory and impact of artificial intelligence.",
  },
];
const chats = [
  {
    id: "chat1",
    title: "كيف أستخدم البحث الدلالي في أخباري؟",
    updated_at: now,
  },
  {
    id: "chat2",
    title: "A calmer way to keep up with technology",
    updated_at: now,
  },
];
const digest = {
  enabled: !firstRun,
  language: "ar",
  engine: firstRun ? "provider" : "local",
  local_model: firstRun ? "" : "qwen3.5:2b",
  phase: firstRun ? "disabled" : "ready",
  prepared: firstRun ? 0 : 3,
  pending: 0,
};
const profiles = [
  {
    id: "p1",
    label: longNames
      ? "My workspace account · research-and-editorial-team-with-a-long-address@example.com"
      : "My OpenAI account",
    provider_key: "openai",
    model_id: "gpt-5.4",
    connection: { state: "connected" },
    usage_today: 4,
  },
];
let draftText =
  "## فكرة تستحق الاحتفاظ بها\n\nالأخبار تصبح أكثر فائدة عندما نربطها بالسياق ونراجع مصادرها.";
mockIPC(
  async (cmd, args) => {
    if (cmd !== "engine_call") {
      if (cmd === "previous_unclean_exit") return false;
      if (cmd === "diagnostics_report")
        return "openNews QA fixture · No user data\nStatus: ready";
      if (cmd === "check_update") return { update: null };
      return null;
    }
    const { command, payload: p = {} } = args as {
      command: string;
      payload: any;
    };
    switch (command) {
      case "runtime.health":
        return { ok: true };
      case "workspace.snapshot":
        return {
          profiles: firstRun ? [] : profiles,
          subscriptions: firstRun ? [] : feeds.slice(0, 2),
          assignments: [],
          jobs: [],
          drafts: [
            {
              id: "d1",
              topic: "لماذا نحتاج إلى سياق الأخبار؟",
              format: "linkedin",
              updated_at: now,
              text: draftText,
            },
          ],
          sources: [],
          news_digest: digest,
        };
      case "chat.list":
        return {
          conversations: firstRun
            ? []
            : chats.map((chat, i) => ({
                ...chat,
                active_job_id:
                  activityMode === "running" && i === 0 ? "qa-job" : undefined,
              })),
        };
      case "chat.progress":
        return {
          state: "running",
          elapsed_seconds: 13,
          execution: qaExecution,
          message: "",
        };
      case "chat.detail":
        if (p.before_message_id) {
          await new Promise((resolve) => setTimeout(resolve, 700));
          return {
            id: p.conversation_id,
            has_more: false,
            messages: [
              {
                id: "earlier1",
                role: "assistant",
                content: "Earlier fixture message",
              },
            ],
          };
        }
        return {
          id: p.conversation_id,
          title: chats.find((c) => c.id === p.conversation_id)?.title,
          has_more: params.has("earlier"),
          next_before_message_id: params.has("earlier") ? "m1" : undefined,
          last_job:
            activityMode === "failed" || activityMode === "cancelled"
              ? { state: activityMode, error_code: "MODEL_UNSUPPORTED" }
              : undefined,
          messages: [
            {
              id: "m1",
              role: "user",
              content: "كيف أقدر أبحث في الأخبار بالمعنى؟",
            },
            {
              id: "m2",
              role: "assistant",
              activity: activityMode === "completed" ? qaExecution : undefined,
              content:
                '## البحث بالمعنى\n\nيربط البحث الدلالي فكرتك بالأخبار ذات الصلة، حتى عندما تستخدم كلمات مختلفة.\n\n- يحتفظ التطبيق بنص المقالة ومصدرها.\n- ينشئ نموذج التضمين تمثيلًا رقميًا للنص.\n- يقارن معنى سؤالك بالمقالات المفهرسة.\n\n```python\nresults = search("local language models")\nfor article in results:\n    print(article.title)\n```',
              citations: [
                { title: "Ollama Blog", url: "https://ollama.com/blog" },
              ],
            },
          ].filter(
            (message) =>
              !["running", "failed", "cancelled"].includes(
                activityMode || "",
              ) || message.role === "user",
          ),
        };
      case "providers.models":
        if (params.get("models") === "retry" && ++modelAttempts === 1)
          throw new Error("Model directory unavailable");
        return {
          models: [
            {
              id: "gpt-5.4",
              name: longNames
                ? "A reasoning model with a long release name for multilingual editorial work"
                : "GPT-5.4",
            },
            { id: "gpt-5.4-mini", name: "GPT-5.4 mini" },
          ],
        };
      case "agents.list":
        return {
          agents: longNames
            ? [
                {
                  id: "qa-assistant",
                  name: "مساعد للتحليل والكتابة ومراجعة الأخبار والمصادر ذات الأسماء الطويلة",
                  profile_id: "p1",
                  model_id: "gpt-5.4",
                },
              ]
            : [],
        };
      case "news.list":
        return {
          articles: firstRun
            ? []
            : articles.filter(
                (a) =>
                  !p.query ||
                  a.title.toLowerCase().includes(p.query.toLowerCase()),
              ),
          has_more: false,
        };
      case "news.related":
        return { articles: articles.filter((row) => row.id !== p.article_id) };
      case "news.update": {
        const source = feeds.find((row) => row.id === p.subscription_id);
        if (source) Object.assign(source, p);
        return {};
      }
      case "news.article":
      case "news.reader":
        return {
          ...articles.find((a) => a.id === p.article_id),
          text: "## الفكرة الأساسية\n\nهذا المحتوى مثال لاختبار واجهة القارئ، ولا يمثل نص المقالة الأصلية.\n\nنستخدم الفقرات والقوائم والروابط لفحص القراءة، مع عرض <u>التنسيق</u> كما يظهر داخل المصدر.\n\n- السياق والمصدر\n- القراءة والتحليل\n- العودة إلى المحادثة",
          reader: { blocks: [] },
          prepared_summary: {
            summary:
              "## الخلاصة\n\nملخص تجريبي لواجهة القراءة، وليس خبرًا حقيقيًا.\n\n### تسلسل التفاصيل\n\n- يوضح المقال الفكرة الأساسية وأسبابها. [S1]\n- يضيف المصدر المرتبط سياقًا مختلفًا، مع توضيح ما لم يتأكد بعد. [S2]",
            sources: [
              {id:"S1",url:"https://example.com/article",status:"read"},
              {id:"S2",url:"https://example.org/report",status:"read"},
              {id:"S3",url:"https://x.com/example/status/1",status:"unavailable"},
            ],
            quotes: [{source_id:"S2",text:"هذا اقتباس اصطناعي لاختبار الواجهة فقط.",url:"https://example.org/report"}],
            coverage: {limited:false,unvisited_links:0},
          },
        };
      case "news.summary.states":
        return { states: { a1: "ready", a2: "ready", a3: "ready" } };
      case "news.digest.status":
        return digest;
      case "news.search.status":
        return {
          enabled: true,
          model: "embeddinggemma-2:270m",
          phase: "ready",
          indexed: 3,
          semantic: 3,
          pending: 0,
        };
      case "news.search.inspect":
        return {
          articles: articles.map((article, i) => ({
            ...article,
            segments: 4 + i,
            embedded: 4 + i,
          })),
        };
      case "news.local.policy":
        return localPolicy;
      case "news.local.policy.set":
        localPolicy = {
          ...localPolicy,
          ...p,
          phase: p.paused === true ? "paused" : "ready",
        };
        return localPolicy;
      case "news.local.status":
        if (params.get("local") === "loading") await new Promise(() => {});
        if (params.get("local") === "failed")
          throw new Error("Fixture: runtime unavailable");
        return {
          runtime: true,
          installed: [
            ...localModels,
            { id: "embeddinggemma-2:270m", size: 378346995 },
          ],
          models: localModels,
          download: localDownload,
        };
      case "news.local.search":
        return {
          models: Array.from({ length: 16 }, (_, index) => ({
            id: "example-model-" + index,
            name: "Example multilingual model " + (index + 1),
            description:
              "A deliberately long catalog description to verify wrapping and stable result heights in the real settings component. This is synthetic visual test data.",
          })),
          has_more: false,
        };
      case "news.local.available":
        return {
          installed: [
            ...localModels,
            {
              id: "embeddinggemma-2:270m",
              size: 378346995,
              capabilities: ["embedding"],
            },
          ],
        };
      case "news.local.inspect":
        return {
          id: p.model,
          size: 1.6e9,
          free_disk: 80e9,
          required_disk: 3.6e9,
          estimated_memory: 3e9,
          fit: "fits",
          can_download: true,
        };
      case "news.local.download":
        localDownload = {
          ...localDownload,
          phase: "checking",
          model: p.model,
          completed: 0,
        };
        return { download: localDownload };
      case "news.local.cancel":
        localDownload = { ...localDownload, phase: "cancelled" };
        return { download: localDownload };
      case "news.curated":
        return { feeds };
      case "news.directory":
        return { feeds, provider: "RSS.mobi" };
      case "news.related":
        return { articles: [] };
      case "news.history":
        return {
          revisions: [
            { id: 2, captured_at: now },
            { id: 1, captured_at: now },
          ],
        };
      case "news.revision":
        return {
          id: p.revision_id,
          previous_id: p.revision_id === 1 ? null : 1,
          content: {
            title: "نسخة محفوظة لاختبار القارئ",
            text: "النص المحفوظ في النسخة الأولى، للمقارنة مع التحديثات اللاحقة.",
          },
          diff: "--- title (before)\n+++ title (after)\n@@ -1 +1 @@\n-العنوان السابق\n+عنوان المقالة بعد التحديث\n--- text (before)\n+++ text (after)\n@@ -1,2 +1,2 @@\n فقرة توضح السياق العام للمقالة.\n-النص السابق\n+أضيفت تفاصيل إلى المقالة.",
          captured_at: now,
        };
      case "providers.catalog":
        return {
          providers: [
            {
              id: "openai",
              name: "OpenAI",
              status: "ready",
              credential: "api_key",
              credential_fields: ["api_key"],
              fields: [],
            },
            {
              id: "ollama",
              name: "Ollama",
              status: "ready",
              credential: "local_server",
              fields: ["host"],
            },
          ],
        };
      case "providers.check":
        return { state: "connected" };
      case "assistant.get":
        return {
          settings: {
            role: "مساعد يساعدك على فهم الأخبار ومناقشة الأفكار.",
            instructions: "اشرح الفكرة بسياق واضح، واذكر حدود المصادر.",
          },
          inherited: {},
        };
      case "skills.catalog":
        return { skills: [...skillRows, ...addedSkills] };
      case "skills.search":
        return {
          skills: [
            {
              id: "example/editorial/article-writing",
              title: "article-writing",
              repository: "example/editorial",
              source_url: "https://skills.sh/example/editorial/article-writing",
            },
            {
              id: "example/editorial/content-research",
              title: "content-research",
              repository: "example/editorial",
              source_url:
                "https://skills.sh/example/editorial/content-research",
            },
            {
              id: "example/editorial/newsletter",
              title: "newsletter",
              repository: "example/editorial",
              source_url: "https://skills.sh/example/editorial/newsletter",
            },
          ],
          source: "skills.sh",
        };
      case "skills.preview":
        return {
          kind: "skill",
          id: "article-writing",
          title: "article-writing",
          description:
            "Write articles and newsletters with a clear voice and source-backed facts.",
          content:
            "# Article writing\n\nPreserve supplied facts and sources. Develop each idea clearly. Never invent personal experiences.",
          repository: "example/editorial",
          source_url:
            "https://github.com/example/editorial/blob/fixture/skills/article-writing/SKILL.md",
          source_sha: "fixture",
          license: "MIT",
          supporting_files: true,
        };
      case "skills.add":
        if (addedSkills.some((row) => row.id === p.id))
          throw new Error("This command is already in your library.");
        addedSkills.push({
          ...p,
          title_ar: p.title,
          title_en: p.title,
          description_ar: p.description,
          description_en: p.description,
          origin: "custom",
        });
        return { id: p.id };
      case "skills.remove":
        addedSkills = addedSkills.filter((row) => row.id !== p.id);
        return { removed: p.id };
      case "instructions.get":
        return {
          content:
            "# تعليمات الشرح\n\nاشرح المقالة وأفكارها بالتفصيل، مع الحفاظ على المصدر.",
        };
      case "drafts.detail":
        return {
          draft: {
            id: "d1",
            topic: "لماذا نحتاج إلى سياق الأخبار؟",
            current_version_id: "v1",
          },
          versions: [{ id: "v1", text: draftText, created_at: now }],
        };
      case "drafts.save":
        draftText = p.text;
        return { version_id: "v2" };
      case "daily.get":
        return {
          settings: {
            enabled: false,
            hour: 10,
            minute: 0,
            timezone: "Asia/Riyadh",
            language: "ar",
          },
          reports: params.has("reports")
            ? [
                {
                  day: "2026-10-24",
                  state: "ready",
                  body: "## أخبار اليوم\n\nتقرير تجريبي في مساحة الفحص المعزولة، لمراجعة عرض النص والروابط والقوائم.\n\n- سياق واضح للأخبار\n- المصادر متاحة للمراجعة",
                },
                { day: "2026-10-23", state: "failed", body: "" },
              ]
            : [],
        };
      default:
        return {};
    }
  },
  { shouldMockEvents: true },
);
await import("../src/main");
if (params.has("settings")) {
  const showSettings = () => {
    const button = [
      ...document.querySelectorAll<HTMLButtonElement>(".sidebar button"),
    ].find((node) =>
      ["Settings", "الإعدادات"].includes(node.textContent?.trim() || ""),
    );
    if (!button) return false;
    button.click();
    return true;
  };
  if (!showSettings()) {
    const observer = new MutationObserver(() => {
      if (showSettings()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
}
