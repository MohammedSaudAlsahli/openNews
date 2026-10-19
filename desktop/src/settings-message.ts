import { t } from "./locale";
export function settingsMessage(message: string) {
  if (message.includes("MODEL_UNSUPPORTED"))
    return t(
      "This model is not available yet. Download it or choose an installed model below.",
    );
  if (message.includes("BUSY"))
    return t("Another task is running. Wait for it to finish, then try again.");
  return message.replace(/^Error:\s*/, "");
}
