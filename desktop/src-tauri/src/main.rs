#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde_json::{json, Value};
use std::{io::{BufRead, BufReader, Write, Read}, os::unix::{net::UnixStream, fs::PermissionsExt}, path::PathBuf, process::{Child, Command, Stdio}, sync::Mutex, time::{Duration, Instant}};
use tauri::Manager;

const MAX_FRAME: usize = 1024 * 1024;
struct Engine { child: Child, socket: PathBuf, _directory: tempfile::TempDir }
impl Drop for Engine {
    fn drop(&mut self) {
        // SIGTERM lets the existing engine persist and close its jobs and database.
        unsafe { libc::kill(self.child.id() as i32, libc::SIGTERM); }
        for _ in 0..50 { if self.child.try_wait().ok().flatten().is_some() { return; } std::thread::sleep(Duration::from_millis(100)); }
        let _ = self.child.kill(); let _ = self.child.wait();
    }
}
#[derive(Default)]
struct Runtime { engine: Mutex<Option<Engine>>, failure: Mutex<Option<String>> }
fn start(resources: PathBuf, workspace: PathBuf) -> Result<Engine, String> {
    std::fs::create_dir_all(&workspace).map_err(|e| e.to_string())?;
    std::fs::set_permissions(&workspace, std::fs::Permissions::from_mode(0o700)).map_err(|e| e.to_string())?;
    let directory = tempfile::Builder::new().prefix("ost-").tempdir_in("/tmp").map_err(|e| e.to_string())?;
    let socket = directory.path().join("engine.sock");
    let python = resources.join("python/bin/python3.12");
    let entry = resources.join("engine/bootstrap.py");
    let home = std::env::var("HOME").map_err(|_| "Home directory unavailable")?;
    let child = Command::new(python).args(["-I", "-B"]).arg(entry)
        .arg("--workspace").arg(&workspace).arg("--socket").arg(&socket)
        .env_clear().env("HOME", home).env("PATH", "/usr/bin:/bin").env("LANG", "en_US.UTF-8").env("AGNO_TELEMETRY", "false")
        .stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null()).spawn()
        .map_err(|_| "The bundled engine is missing. Run the runtime staging script and rebuild.".to_string())?;
    let mut engine = Engine { child, socket, _directory: directory };
    let deadline = Instant::now() + Duration::from_secs(30);
    while Instant::now() < deadline {
        if engine.child.try_wait().map_err(|e| e.to_string())?.is_some() { return Err("Engine stopped. The preview workspace may already be open.".into()); }
        if engine.socket.exists() { return Ok(engine); }
        std::thread::sleep(Duration::from_millis(50));
    }
    Err("Engine startup timed out.".into())
}
fn exchange(path: PathBuf, command: String, payload: Value) -> Result<Value, String> {
    if command.len() > 80 || !command.chars().all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '_') || !payload.is_object() { return Err("Invalid request".into()); }
    let id = uuid::Uuid::new_v4().to_string();
    let mut frame = serde_json::to_vec(&json!({"schema_version":1,"request_id":id,"command":command,"payload":payload})).map_err(|e| e.to_string())?;
    frame.push(b'\n'); if frame.len() > MAX_FRAME { return Err("Request exceeds the engine limit".into()); }
    let mut stream = UnixStream::connect(path).map_err(|_| "Engine disconnected".to_string())?;
    stream.set_read_timeout(Some(Duration::from_secs(130))).map_err(|e| e.to_string())?;
    stream.set_write_timeout(Some(Duration::from_secs(10))).map_err(|e| e.to_string())?;
    stream.write_all(&frame).map_err(|_| "Could not send request".to_string())?;
    let mut answer = Vec::new();
    BufReader::new(stream).take((MAX_FRAME+1) as u64).read_until(b'\n', &mut answer).map_err(|_| "The engine did not reply in time".to_string())?;
    if answer.len() > MAX_FRAME || answer.last() != Some(&b'\n') { return Err("Invalid engine response".into()); }
    let value: Value = serde_json::from_slice(&answer).map_err(|_| "Invalid engine JSON".to_string())?;
    if value["request_id"] != id || value["schema_version"] != 1 { return Err("Engine response mismatch".into()); }
    if value["event"] == "failed" { return Err(format!("{} ({})", value["error"]["message"].as_str().unwrap_or("Request failed"), value["error"]["code"].as_str().unwrap_or("ERROR"))); }
    Ok(value["result"].clone())
}
#[tauri::command]
async fn engine_call(state: tauri::State<'_, Runtime>, command: String, payload: Value) -> Result<Value, String> {
    let socket = state.engine.lock().map_err(|_| "Engine lock failed")?.as_ref().map(|e| e.socket.clone());
    let socket = socket.ok_or_else(|| state.failure.lock().ok().and_then(|e| e.clone()).unwrap_or("Engine is starting…".into()))?;
    tauri::async_runtime::spawn_blocking(move || exchange(socket, command, payload)).await.map_err(|e| e.to_string())?
}
#[tauri::command]
async fn article_image(app: tauri::AppHandle, state: tauri::State<'_, Runtime>, article_id: String, image_id: String) -> Result<String, String> {
    let socket = state.engine.lock().map_err(|_| "Engine lock failed")?.as_ref().map(|e| e.socket.clone()).ok_or("Engine not ready")?;
    let root = app.path().app_data_dir().map_err(|e| e.to_string())?.join("default/reader-images");
    tauri::async_runtime::spawn_blocking(move || {
        use base64::Engine;
        let result = exchange(socket, "news.image".into(), json!({"article_id":article_id,"image_id":image_id}))?;
        let path = PathBuf::from(result["path"].as_str().ok_or("No image path")?).canonicalize().map_err(|e| e.to_string())?;
        if !path.starts_with(root.canonicalize().map_err(|e| e.to_string())?) { return Err("Image outside cache".into()); }
        let bytes = std::fs::read(path).map_err(|e| e.to_string())?;
        if bytes.len() > 4*1024*1024 { return Err("Image too large".into()); }
        let mime = if bytes.starts_with(b"\x89PNG") { "image/png" } else if bytes.starts_with(b"\xff\xd8") { "image/jpeg" } else if bytes.starts_with(b"GIF8") { "image/gif" } else if bytes.starts_with(b"RIFF") { "image/webp" } else { "image/avif" };
        Ok(format!("data:{};base64,{}",mime,base64::engine::general_purpose::STANDARD.encode(bytes)))
    }).await.map_err(|e|e.to_string())?
}
#[tauri::command]
fn open_external(address: String) -> Result<(), String> {
    let url = url::Url::parse(&address).map_err(|_| "Invalid URL")?;
    if !matches!(url.scheme(),"https"|"http") || !url.username().is_empty() || url.password().is_some() { return Err("Unsupported URL".into()); }
    Command::new("/usr/bin/open").arg(url.as_str()).spawn().map_err(|e|e.to_string())?;
    Ok(())
}
fn main() {
    let app = tauri::Builder::default().manage(Runtime::default())
        .invoke_handler(tauri::generate_handler![engine_call, article_image, open_external])
        .setup(|app| {
            let handle = app.handle().clone();
            let bundled = app.path().resource_dir()?.join("runtime");
            let resources = if bundled.join("python/bin/python3.12").exists() { bundled } else if cfg!(debug_assertions) { PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("runtime") } else { bundled };
            let workspace = app.path().app_data_dir()?.join("default");
            tauri::async_runtime::spawn_blocking(move || {
                let state = handle.state::<Runtime>();
                match start(resources, workspace) {
                    Ok(engine) => *state.engine.lock().unwrap() = Some(engine),
                    Err(error) => *state.failure.lock().unwrap() = Some(error),
                }
            });
            Ok(())
        }).build(tauri::generate_context!()).expect("Could not create OpenStudio window");
    app.run(|handle, event| match event {
        tauri::RunEvent::WindowEvent { label, event: tauri::WindowEvent::CloseRequested { api, .. }, .. } => {
            api.prevent_close(); if let Some(window) = handle.get_webview_window(&label) { let _ = window.hide(); }
        },
        tauri::RunEvent::Reopen { .. } => { if let Some(window) = handle.get_webview_window("main") { let _ = window.show(); let _ = window.set_focus(); } },
        tauri::RunEvent::Exit => { handle.state::<Runtime>().engine.lock().unwrap().take(); },
        _ => {}
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn embedded_engine_keeps_data_across_restarts() {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("runtime");
        if !root.join("python/bin/python3.12").exists() { panic!("Stage the embedded runtime before testing"); }
        let workspace = tempfile::tempdir().unwrap();
        let engine = start(root.clone(),workspace.path().into()).unwrap();
        let health = exchange(engine.socket.clone(),"runtime.health".into(),json!({})).unwrap();
        assert_eq!(health["schema_version"],1);
        assert!(health["sqlite_vec"].is_string());
        let chat = exchange(engine.socket.clone(),"chat.create".into(),json!({"title":"اختبار جلسة محفوظة"})).unwrap();
        let instructions = exchange(engine.socket.clone(),"assistant.get".into(),json!({"scope":"general"})).unwrap();
        assert!(instructions["settings"]["role"].as_str().unwrap().len()>10);
        assert!(exchange(engine.socket.clone(),"chat.detail".into(),json!({"conversation_id":"invalid"})).is_err());
        drop(engine);
        let engine = start(root,workspace.path().into()).unwrap();
        let detail = exchange(engine.socket.clone(),"chat.detail".into(),json!({"conversation_id":chat["conversation_id"]})).unwrap();
        assert_eq!(detail["title"],"اختبار جلسة محفوظة");
    }
    #[test]
    fn bridge_rejects_non_object_payload_and_oversized_frames() {
        assert!(exchange(PathBuf::from("/nonexistent"),"runtime.health".into(),json!(null)).is_err());
        assert!(exchange(PathBuf::from("/nonexistent"),"runtime.health".into(),json!({"text":"a".repeat(MAX_FRAME)})).unwrap_err().contains("limit"));
    }
}
