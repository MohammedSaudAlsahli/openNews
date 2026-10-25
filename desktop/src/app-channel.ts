export const DEVELOPMENT =
  import.meta.env.VITE_OPENNEWS_CHANNEL === "development";
export const APP_NAME = DEVELOPMENT ? "openNews Dev" : "openNews";
