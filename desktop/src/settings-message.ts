import { t } from "./locale";
export function settingsMessage(message: string) {
  if (message.includes("MODEL_UNSUPPORTED"))
    return t(
      "This model is unavailable for this connection. Refresh the model list or choose another model.",
    );
  if (message.includes("BUSY"))
    return t("Another task is running. Wait for it to finish, then try again.");
  return message.replace(/^Error:\s*/, "");
}
