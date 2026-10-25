//! Isolated actual-bundle updater exercise, compiled against the pinned app crates.
//! Never points at /Applications or a user's workspace. See test-update.py.
use serde_json::{json, Value};
use std::path::PathBuf;
use tauri_plugin_updater::UpdaterExt;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let config: Value = serde_json::from_slice(&std::fs::read(&args[1]).unwrap()).unwrap();
    let manifest: Value = serde_json::from_slice(&std::fs::read(&args[2]).unwrap()).unwrap();
    let app_path = PathBuf::from(&args[3]);
    assert!(app_path.to_string_lossy().starts_with("/tmp/opennews-update-qa-"));
    assert!(!app_path.components().any(|p| matches!(p, std::path::Component::ParentDir)));
    assert!(!std::fs::symlink_metadata(&app_path).unwrap().file_type().is_symlink());
    assert_eq!(app_path.file_name().unwrap(), "openNews.app");
    let old_version = &args[4];
    let mut context = tauri::test::mock_context(tauri::test::noop_assets());
    context.package_info_mut().version = old_version.parse().unwrap();
    context.config_mut().plugins.0.insert("updater".into(), config["plugins"]["updater"].clone());
    let app = tauri::test::mock_builder()
        .plugin(tauri_plugin_updater::Builder::new().pubkey(config["plugins"]["updater"]["pubkey"].as_str().unwrap()).build())
        .build(context).unwrap();
    let updater = app.updater_builder()
        .executable_path(app_path.join("Contents/MacOS/openstudio-desktop"))
        .build().unwrap();
    if args[5] == "check" || args[5] == "current" {
        let result = tauri::async_runtime::block_on(updater.check()).unwrap();
        if args[5] == "current" {
            assert!(result.is_none(), "Current version must not offer itself again");
            println!("{}", json!({"current_version_check":"passed","version":old_version}));
            return;
        }
        let update = result.expect("Expected official update for the old installed version");
        assert_eq!(update.version, manifest["version"].as_str().unwrap());
        println!("{}", json!({"network_check":"passed","from":old_version,"to":update.version}));
        return;
    }
    let bytes = if args[5] == "download" {
        tauri::async_runtime::block_on(async {
            let remote = updater.check().await.unwrap().expect("Expected update from public feed");
            assert_eq!(remote.version, manifest["version"].as_str().unwrap());
            remote.download(|_, _| {}, || {}).await.unwrap()
        })
    } else { std::fs::read(&args[5]).unwrap() };
    let before = std::fs::read(app_path.join("Contents/Info.plist")).unwrap();
    let update = updater.restore_update(manifest.clone()).unwrap().unwrap();
    let mut tampered = bytes.clone();
    tampered[20] ^= 1;
    assert!(update.install(tampered).is_err());
    assert_eq!(std::fs::read(app_path.join("Contents/Info.plist")).unwrap(), before);
    let mut wrong_version = manifest;
    wrong_version["version"] = json!("999.0.0");
    let invalid = updater.restore_update(wrong_version).unwrap().unwrap();
    assert!(invalid.install(&bytes).is_err());
    assert_eq!(std::fs::read(app_path.join("Contents/Info.plist")).unwrap(), before);
    update.install(&bytes).unwrap();
    println!("{}", json!({"signed_bundle_install":"passed","tamper_rejected":true,"version_mismatch_rejected":true,"from":old_version,"to":update.version}));
}
