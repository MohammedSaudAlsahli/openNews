import { useEffect, useState, useRef } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { t } from "./locale";

/** Navigation is cancellable, so a page never needs to discard edits to switch. */
const guards = new Map<symbol, (proceed: () => void) => void>();
export function navigateSafely(action: () => void) {
  const pending = [...guards.values()];
  const next = (index: number) => {
    if (index === pending.length) action();
    else pending[index](() => next(index + 1));
  };
  next(0);
}
export function useUnsavedChanges(
  dirty: boolean,
  save: () => Promise<boolean>,
) {
  const [next, setNext] = useState<(() => void) | null>(null),
    [saving, setSaving] = useState(false);
  const dirtyRef = useRef(dirty);
  dirtyRef.current = dirty;
  useEffect(() => {
    const id = Symbol("unsaved");
    guards.set(id, (proceed) => {
      if (dirtyRef.current) setNext(() => proceed);
      else proceed();
    });
    return () => {
      guards.delete(id);
    };
  }, []);
  useEffect(() => {
    if (!dirty) return;
    function unload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", unload);
    return () => {
      window.removeEventListener("beforeunload", unload);
    };
  }, [dirty]);
  const confirm = (action: () => void) => {
    if (dirty) setNext(() => action);
    else action();
  };
  const dialog = (
    <Dialog.Root
      open={Boolean(next)}
      onOpenChange={(open) => {
        if (!open && !saving) setNext(null);
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-panel">
          <Dialog.Title>{t("Save your changes?")}</Dialog.Title>
          <Dialog.Description>
            {t("You have changes that have not been saved yet.")}
          </Dialog.Description>
          <div className="dialog-actions">
            <button disabled={saving} onClick={() => setNext(null)}>
              {t("Keep editing")}
            </button>
            <button
              disabled={saving}
              onClick={() => {
                const action = next;
                setNext(null);
                action?.();
              }}
            >
              {t("Discard changes")}
            </button>
            <button
              className="primary"
              disabled={saving}
              onClick={async () => {
                setSaving(true);
                try {
                  if (await save()) {
                    const action = next;
                    setNext(null);
                    action?.();
                  }
                } finally {
                  setSaving(false);
                }
              }}
            >
              {t(saving ? "Saving…" : "Save and continue")}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
  return { confirm, dialog };
}
