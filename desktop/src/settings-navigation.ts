import {
  Calendar,
  Cpu,
  Newspaper,
  Settings2,
  SlidersHorizontal,
} from "lucide-react";

// Keep the persisted destinations stable; the rail groups them around user tasks.
export const settingsCategories = [
  {
    id: "general",
    title: "General",
    description: "Language, appearance & privacy",
    icon: Settings2,
    pages: [
      {
        id: "appearance",
        title: "Appearance & language",
        keywords: ["Light", "Dark", "Interface language"],
      },
      {
        id: "privacy",
        title: "Privacy & updates",
        keywords: [
          "Updates",
          "Import original workspace",
          "Restore previous workspace",
        ],
      },
    ],
  },
  {
    id: "models",
    title: "AI models",
    description: "On your Mac or connected accounts",
    icon: Cpu,
    pages: [
      {
        id: "local-models",
        title: "Local models",
        keywords: [
          "Performance",
          "Quiet",
          "Balanced",
          "Process on battery power",
          "Background processing",
          "Pause",
          "Download",
        ],
      },
      {
        id: "connections",
        title: "Accounts & models",
        keywords: ["API key", "Providers", "Sign in", "Connection", "Model"],
      },
    ],
  },
  {
    id: "assistant",
    title: "Assistant & writing",
    description: "Instructions, style & writing skills",
    icon: SlidersHorizontal,
    pages: [
      {
        id: "instructions",
        title: "Customize assistant",
        keywords: [
          "Role & expertise",
          "Working instructions",
          "Writing style",
          "Examples",
          "Sources & knowledge",
          "Response format",
          "Technical instructions",
        ],
      },
      {
        id: "skills",
        title: "Writing skills",
        keywords: ["Research", "Summarize", "Rewrite", "Skill"],
      },
    ],
  },
  {
    id: "articles",
    title: "Your articles",
    description: "Search & automatic summaries",
    icon: Newspaper,
    pages: [
      {
        id: "search",
        title: "Article search",
        keywords: ["Search by meaning", "Indexing"],
      },
      {
        id: "summaries",
        title: "TL;DR",
        keywords: ["Automatic summaries", "Language", "Summary source"],
      },
    ],
  },
  {
    id: "daily",
    title: "Daily report",
    description: "Schedule & saved reports",
    icon: Calendar,
    pages: [
      {
        id: "daily",
        title: "Daily report",
        keywords: ["Report time", "Time zone", "Language", "Save schedule"],
      },
    ],
  },
];
