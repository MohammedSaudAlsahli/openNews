use serde_json::{json, Value};
use std::{sync::Mutex, time::Duration};
use tauri::{Emitter, Manager};
use tauri_plugin_updater::{Update, UpdaterExt};
#[derive(Default)]
pub struct Pending(pub Mutex<Option<Update>>);
#[tauri::command]
pub async fn check_update(
    app: tauri::AppHandle,
    pending: tauri::State<'_, Pending>,
) -> Result<Value, String> {
    let update = app.updater_builder().timeout(Duration::from_secs(20)).build().map_err(|e| e.to_string())?.check().await.map_err(|_| "The Tauri update channel is not available yet. This does not mean your app is up to date.".to_string())?;
    let metadata = update
        .as_ref()
        .map(|u| json!({"version":u.version,"notes":u.body}));
    *pending.0.lock().map_err(|_| "Update state unavailable")? = update;
    Ok(json!({"update":metadata,"current_version":app.package_info().version.to_string()}))
}
#[tauri::command]
pub async fn install_update(
    app: tauri::AppHandle,
    pending: tauri::State<'_, Pending>,
) -> Result<(), String> {
    let update = pending
        .0
        .lock()
        .map_err(|_| "Update state unavailable")?
        .take()
        .ok_or("Check for an update first")?;
    let mut downloaded = 0usize;
    // Download and validate the mandatory signature before touching the application.
    let bytes = update
        .download(
            |chunk, total| {
                downloaded += chunk;
                let _ = app.emit(
                    "update-progress",
                    json!({"downloaded":downloaded,"total":total}),
                );
            },
            || {},
        )
        .await
        .map_err(|e| e.to_string())?;
    // No running engine remains inside an application being replaced.
    let runtime = app.state::<crate::Runtime>();
    let mut engine = runtime.engine.lock().map_err(|_| "Workspace busy")?;
    let workspace = app
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?
        .join("default");
    let resources = app
        .path()
        .resource_dir()
        .map_err(|e| e.to_string())?
        .join("runtime");
    let old = engine.take().ok_or("Engine is not ready")?;
    drop(old);
    if let Err(error) = update.install(bytes) {
        *engine = crate::start(resources, workspace).ok();
        return Err(error.to_string());
    }
    drop(engine);
    app.restart();
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn signed_update_replaces_one_bundle_and_rejects_tampering() {
        let config: Value = serde_json::from_str(include_str!("../tauri.conf.json")).unwrap();
        let mut context = tauri::test::mock_context(tauri::test::noop_assets());
        context
            .config_mut()
            .plugins
            .0
            .insert("updater".into(), config["plugins"]["updater"].clone());
        let app = tauri::test::mock_builder()
            .plugin(
                tauri_plugin_updater::Builder::new()
                    .pubkey(config["plugins"]["updater"]["pubkey"].as_str().unwrap())
                    .build(),
            )
            .build(context)
            .unwrap();
        let temp = tempfile::tempdir().unwrap();
        let installed = temp
            .path()
            .join("OpenStudio Preview.app/Contents/MacOS/openstudio-desktop");
        std::fs::create_dir_all(installed.parent().unwrap()).unwrap();
        std::fs::write(&installed, "old-fixture").unwrap();
        let data = temp.path().join("workspace.sqlite");
        std::fs::write(&data, "retained-user-data").unwrap();
        let updater = app
            .updater_builder()
            .target("fixture")
            .executable_path(&installed)
            .endpoints(vec!["https://example.invalid/update".parse().unwrap()])
            .unwrap()
            .build()
            .unwrap();
        let update = updater.restore_update(json!({"version":"999.0.0","platforms":{"fixture":{"url":"https://example.invalid/update.tar.gz","signature":include_str!("../tests/fixtures/signed-update.tar.gz.sig").trim()}}})).unwrap().unwrap();
        let bytes = include_bytes!("../tests/fixtures/signed-update.tar.gz");
        let mut tampered = bytes.to_vec();
        tampered[20] ^= 1;
        assert!(update.install(tampered).is_err());
        assert_eq!(std::fs::read_to_string(&installed).unwrap(), "old-fixture");
        update.install(bytes).unwrap();
        assert_eq!(
            std::fs::read_to_string(&installed).unwrap(),
            "updated-fixture"
        );
        assert_eq!(std::fs::read_to_string(data).unwrap(), "retained-user-data");
        assert_eq!(
            std::fs::read_dir(temp.path())
                .unwrap()
                .filter(|p| p
                    .as_ref()
                    .unwrap()
                    .path()
                    .extension()
                    .is_some_and(|s| s == "app"))
                .count(),
            1
        );
    }
}

pub async fn notify_available(app: tauri::AppHandle) {
    // A missing preview feed is not an update and must not interrupt normal work.
    if let Ok(result) = check_update(app.clone(), app.state::<Pending>()).await {
        if let Some(version) = result["update"]["version"].as_str() {
            let _ = app.emit("update-available", json!({"version":version}));
        }
    }
}
