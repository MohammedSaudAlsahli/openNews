import { type ReactNode } from "react";
import * as Tooltip from "@radix-ui/react-tooltip";
import {
  Activity,
  Compass,
  FileText,
  HelpCircle,
  MessageSquare,
  Newspaper,
  PanelLeftOpen,
  Plus,
  Settings,
} from "lucide-react";
import { t, useLocale } from "./locale";

// The compact shell keeps the same guarded navigation as the expanded sidebar.
export function NavigationRail({
  page,
  onNavigate,
  onNew,
  onExpand,
  onHelp,
  busy,
}: {
  page: string;
  onNavigate: (page: string) => void;
  onNew: () => void;
  onExpand: () => void;
  onHelp: () => void;
  busy: number;
}) {
  const locale = useLocale();
  const action = (
    label: string,
    icon: ReactNode,
    onClick: () => void,
    current = false,
  ) => (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button
          className={current ? "selected" : undefined}
          aria-label={t(label)}
          aria-current={current ? "page" : undefined}
          onClick={onClick}
        >
          {icon}
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          className="rail-tooltip"
          side={locale === "ar" ? "left" : "right"}
          sideOffset={10}
          collisionPadding={12}
        >
          {t(label)}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
  return (
    <Tooltip.Provider delayDuration={350}>
      <nav className="navigation-rail" aria-label={t("Main navigation")}>
        <div className="rail-primary">
          {action("Show sidebar", <PanelLeftOpen size={19} />, onExpand)}
          {action("New conversation", <Plus size={20} />, onNew)}
          {action(
            "Conversations",
            <MessageSquare size={19} />,
            onExpand,
            page === "chat",
          )}
          {action(
            "Articles",
            <Newspaper size={19} />,
            () => onNavigate("articles"),
            page === "articles",
          )}
          {action(
            "Sources",
            <Compass size={19} />,
            () => onNavigate("sources"),
            page === "sources",
          )}
          {action(
            "Saved drafts",
            <FileText size={19} />,
            () => onNavigate("drafts"),
            page === "drafts",
          )}
        </div>
        <div className="rail-secondary">
          {action(
            "Background activity",
            <>
              <Activity size={19} />
              {busy > 0 && <span className="rail-busy" aria-hidden="true" />}
            </>,
            () => onNavigate("activity"),
            page === "activity",
          )}
          {action(
            "Settings",
            <Settings size={19} />,
            () => onNavigate("settings"),
            page === "settings",
          )}
          {action("Help & diagnostics", <HelpCircle size={19} />, onHelp)}
        </div>
      </nav>
    </Tooltip.Provider>
  );
}
