#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod credentials;
mod updates;
use serde_json::{json, Value};
use std::{
    io::{BufRead, BufReader, Read, Write},
    os::unix::{fs::PermissionsExt, net::UnixStream},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
    time::{Duration, Instant},
};
use tauri::{Emitter, Manager};
use tauri_plugin_notification::NotificationExt;

const MAX_FRAME: usize = 1024 * 1024;
struct Engine {
    child: Child,
    socket: PathBuf,
    _directory: tempfile::TempDir,
}
impl Drop for Engine {
    fn drop(&mut self) {
        // SIGTERM lets the existing engine persist and close its jobs and database.
        unsafe {
            libc::kill(self.child.id() as i32, libc::SIGTERM);
        }
        for _ in 0..50 {
            if self.child.try_wait().ok().flatten().is_some() {
                return;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}
#[derive(Default)]
struct Runtime {
    engine: Mutex<Option<Engine>>,
    failure: Mutex<Option<String>>,
    stopping: std::sync::atomic::AtomicBool,
}
fn start(resources: PathBuf, workspace: PathBuf) -> Result<Engine, String> {
    std::fs::create_dir_all(&workspace).map_err(|e| e.to_string())?;
    std::fs::set_permissions(&workspace, std::fs::Permissions::from_mode(0o700))
        .map_err(|e| e.to_string())?;
    let directory = tempfile::Builder::new()
        .prefix("ost-")
        .tempdir_in("/tmp")
        .map_err(|e| e.to_string())?;
    let socket = directory.path().join("engine.sock");
    let python = resources.join("python/bin/python3.12");
    let entry = resources.join("engine/bootstrap.py");
    let home = std::env::var("HOME").map_err(|_| "Home directory unavailable")?;
    let child = Command::new(python)
        .args(["-I", "-B"])
        .arg(entry)
        .arg("--workspace")
        .arg(&workspace)
        .arg("--socket")
        .arg(&socket)
        .env_clear()
        .env("HOME", home)
        .env("PATH", "/usr/bin:/bin")
        .env("LANG", "en_US.UTF-8")
        .env("AGNO_TELEMETRY", "false")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| {
            "The bundled engine is missing. Run the runtime staging script and rebuild.".to_string()
        })?;
    let mut engine = Engine {
        child,
        socket,
        _directory: directory,
    };
    let deadline = Instant::now() + Duration::from_secs(30);
    while Instant::now() < deadline {
        if engine
            .child
            .try_wait()
            .map_err(|e| e.to_string())?
            .is_some()
        {
            return Err("Engine stopped. The preview workspace may already be open.".into());
        }
        if engine.socket.exists() {
            return Ok(engine);
        }
        std::thread::sleep(Duration::from_millis(50));
    }
    Err("Engine startup timed out.".into())
}
fn exchange(path: PathBuf, command: String, payload: Value) -> Result<Value, String> {
    if command.len() > 80
        || !command
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '_')
        || !payload.is_object()
    {
        return Err("Invalid request".into());
    }
    let id = uuid::Uuid::new_v4().to_string();
    let mut frame = serde_json::to_vec(
        &json!({"schema_version":1,"request_id":id,"command":command,"payload":payload}),
    )
    .map_err(|e| e.to_string())?;
    frame.push(b'\n');
    if frame.len() > MAX_FRAME {
        return Err("Request exceeds the engine limit".into());
    }
    let mut stream = UnixStream::connect(path).map_err(|_| "Engine disconnected".to_string())?;
    stream
        .set_read_timeout(Some(Duration::from_secs(130)))
        .map_err(|e| e.to_string())?;
    stream
        .set_write_timeout(Some(Duration::from_secs(10)))
        .map_err(|e| e.to_string())?;
    stream
        .write_all(&frame)
        .map_err(|_| "Could not send request".to_string())?;
    let mut answer = Vec::new();
    BufReader::new(stream)
        .take((MAX_FRAME + 1) as u64)
        .read_until(b'\n', &mut answer)
        .map_err(|_| "The engine did not reply in time".to_string())?;
    if answer.len() > MAX_FRAME || answer.last() != Some(&b'\n') {
        return Err("Invalid engine response".into());
    }
    let value: Value =
        serde_json::from_slice(&answer).map_err(|_| "Invalid engine JSON".to_string())?;
    if value["request_id"] != id || value["schema_version"] != 1 {
        return Err("Engine response mismatch".into());
    }
    if value["event"] == "failed" {
        return Err(format!(
            "{} ({})",
            value["error"]["message"]
                .as_str()
                .unwrap_or("Request failed"),
            value["error"]["code"].as_str().unwrap_or("ERROR")
        ));
    }
    Ok(value["result"].clone())
}
#[tauri::command]
async fn engine_call(
    state: tauri::State<'_, Runtime>,
    command: String,
    payload: Value,
) -> Result<Value, String> {
    let socket = state
        .engine
        .lock()
        .map_err(|_| "Engine lock failed")?
        .as_ref()
        .map(|e| e.socket.clone());
    let socket = socket.ok_or_else(|| {
        state
            .failure
            .lock()
            .ok()
            .and_then(|e| e.clone())
            .unwrap_or("Engine is starting…".into())
    })?;
    tauri::async_runtime::spawn_blocking(move || exchange(socket, command, payload))
        .await
        .map_err(|e| e.to_string())?
}
#[tauri::command]
async fn article_image(
    app: tauri::AppHandle,
    state: tauri::State<'_, Runtime>,
    article_id: String,
    image_id: String,
) -> Result<String, String> {
    let socket = state
        .engine
        .lock()
        .map_err(|_| "Engine lock failed")?
        .as_ref()
        .map(|e| e.socket.clone())
        .ok_or("Engine not ready")?;
    let root = app
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?
        .join("default/reader-images");
    tauri::async_runtime::spawn_blocking(move || {
        use base64::Engine;
        let result = exchange(
            socket,
            "news.image".into(),
            json!({"article_id":article_id,"image_id":image_id}),
        )?;
        let path = PathBuf::from(result["path"].as_str().ok_or("No image path")?)
            .canonicalize()
            .map_err(|e| e.to_string())?;
        if !path.starts_with(root.canonicalize().map_err(|e| e.to_string())?) {
            return Err("Image outside cache".into());
        }
        let bytes = std::fs::read(path).map_err(|e| e.to_string())?;
        if bytes.len() > 4 * 1024 * 1024 {
            return Err("Image too large".into());
        }
        let mime = if bytes.starts_with(b"\x89PNG") {
            "image/png"
        } else if bytes.starts_with(b"\xff\xd8") {
            "image/jpeg"
        } else if bytes.starts_with(b"GIF8") {
            "image/gif"
        } else if bytes.starts_with(b"RIFF") {
            "image/webp"
        } else {
            "image/avif"
        };
        Ok(format!(
            "data:{};base64,{}",
            mime,
            base64::engine::general_purpose::STANDARD.encode(bytes)
        ))
    })
    .await
    .map_err(|e| e.to_string())?
}
fn native_status(helper: &std::path::Path) -> Result<Value, String> {
    let output = Command::new(helper)
        .arg("device")
        .output()
        .map_err(|_| "Device status unavailable")?;
    if !output.status.success() {
        return Err("Device status unavailable".into());
    }
    serde_json::from_slice(&output.stdout).map_err(|_| "Invalid device status".into())
}
fn background(app: tauri::AppHandle, helper: PathBuf, workspace: PathBuf) {
    std::thread::spawn(move || {
        let notified = workspace.join("daily-notified.json");
        let mut next_update = Instant::now();
        let mut last: String = std::fs::read(&notified)
            .ok()
            .and_then(|v| serde_json::from_slice(&v).ok())
            .unwrap_or_default();
        while !app
            .state::<Runtime>()
            .stopping
            .load(std::sync::atomic::Ordering::Relaxed)
        {
            if Instant::now() >= next_update {
                tauri::async_runtime::spawn(updates::notify_available(app.clone()));
                next_update = Instant::now() + Duration::from_secs(6 * 60 * 60);
            }
            let socket = app
                .state::<Runtime>()
                .engine
                .lock()
                .ok()
                .and_then(|e| e.as_ref().map(|e| e.socket.clone()));
            if let Some(socket) = socket {
                if let Ok(device) = native_status(&helper) {
                    let _ = exchange(socket.clone(), "news.digest.device".into(), device);
                }
                if let Ok(status) = exchange(
                    socket.clone(),
                    "daily.check".into(),
                    json!({"consent":true}),
                ) {
                    if status["settings"]["enabled"] == true {
                        if let Some(report) = status["reports"].as_array().and_then(|r| r.first()) {
                            let day = report["day"].as_str().unwrap_or("");
                            if report["state"] == "ready" && !day.is_empty() && day != last {
                                let ar = status["settings"]["language"] == "ar";
                                if app
                                    .notification()
                                    .builder()
                                    .title(if ar {
                                        "تقرير أخبارك اليومي جاهز"
                                    } else {
                                        "Your daily news report is ready"
                                    })
                                    .body(if ar {
                                        "افتح التقرير اليومي في openNews لقراءته."
                                    } else {
                                        "Open Daily report in openNews to read it."
                                    })
                                    .show()
                                    .is_ok()
                                {
                                    last = day.to_string();
                                    if let Ok(mut file) =
                                        tempfile::NamedTempFile::new_in(&workspace)
                                    {
                                        if serde_json::to_writer(&mut file, &last).is_ok()
                                            && file.as_file().sync_all().is_ok()
                                        {
                                            let _ = file.persist(&notified);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                // One leased public page at a time; the helper exits within 12 seconds.
                // Do not compete with inference or run while the device is warm/on low power.
                if native_status(&helper)
                    .is_ok_and(|d| d["thermal"] == "nominal" && d["low_power"] == false)
                {
                    if let Ok(pending) =
                        exchange(socket.clone(), "news.reader.pending".into(), json!({}))
                    {
                        if let (Some(id), Some(url)) = (
                            pending["article"]["id"].as_str(),
                            pending["article"]["url"].as_str(),
                        ) {
                            if let Ok(output) = Command::new(helper.with_file_name("public-reader"))
                                .arg(url)
                                .output()
                            {
                                if output.status.success() && output.stdout.len() <= 1024 * 1024 {
                                    if let Ok(rendered) =
                                        serde_json::from_slice::<Value>(&output.stdout)
                                    {
                                        if rendered["html"]
                                            .as_str()
                                            .is_some_and(|html| !html.is_empty())
                                        {
                                            let _ = exchange(
                                                socket.clone(),
                                                "news.reader.capture".into(),
                                                json!({"article_id":id,"html":rendered["html"]}),
                                            );
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            for _ in 0..10 {
                if app
                    .state::<Runtime>()
                    .stopping
                    .load(std::sync::atomic::Ordering::Relaxed)
                {
                    return;
                }
                std::thread::sleep(Duration::from_secs(1));
            }
        }
    });
}
#[tauri::command]
async fn device_state(app: tauri::AppHandle) -> Result<Value, String> {
    let root = app
        .path()
        .resource_dir()
        .map_err(|e| e.to_string())?
        .join("runtime");
    let helper = if root.join("system-services").exists() {
        root.join("system-services")
    } else {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("runtime/system-services")
    };
    tauri::async_runtime::spawn_blocking(move || {
        let output = Command::new(helper)
            .arg("device")
            .output()
            .map_err(|_| "Device status unavailable")?;
        if !output.status.success() {
            return Err("Device status unavailable".into());
        }
        serde_json::from_slice(&output.stdout).map_err(|_| "Invalid device status".into())
    })
    .await
    .map_err(|e| e.to_string())?
}
#[tauri::command]
async fn export_draft(
    app: tauri::AppHandle,
    state: tauri::State<'_, Runtime>,
    draft_id: String,
) -> Result<String, String> {
    let export = engine_call(state, "drafts.export".into(), json!({"draft_id":draft_id})).await?;
    let directory = app.path().download_dir().map_err(|e| e.to_string())?;
    let path = directory.join(format!("openNews-{}.md", uuid::Uuid::new_v4()));
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .map_err(|_| "Could not save export")?;
    file.write_all(
        export["text"]
            .as_str()
            .ok_or("No export content")?
            .as_bytes(),
    )
    .map_err(|_| "Could not save export")?;
    file.sync_all().map_err(|_| "Could not save export")?;
    Ok(path.to_string_lossy().into_owned())
}
#[tauri::command]
async fn transfer_workspace(app: tauri::AppHandle, restore: bool) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let state = app.state::<Runtime>();
        // Hold the lock through replacement so a second import cannot race this one.
        let mut slot = state.engine.lock().map_err(|_| "Workspace busy")?;
        let bundled = app
            .path()
            .resource_dir()
            .map_err(|e| e.to_string())?
            .join("runtime");
        let resources = if !bundled.join("python/bin/python3.12").exists() && cfg!(debug_assertions)
        {
            PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("runtime")
        } else {
            bundled
        };
        let workspace = app
            .path()
            .app_data_dir()
            .map_err(|e| e.to_string())?
            .join("default");
        let source = app
            .path()
            .home_dir()
            .map_err(|e| e.to_string())?
            .join("Library/Application Support/com.editorialintelligence.studio/default");
        drop(slot.take());
        let result = Command::new(resources.join("python/bin/python3.12"))
            .args(["-I", "-B"])
            .arg(resources.join("engine/workspace_transfer.py"))
            .arg(if restore {
                std::ffi::OsStr::new("--restore")
            } else {
                source.as_os_str()
            })
            .arg(&workspace)
            .output()
            .map_err(|_| "Could not start workspace transfer".to_string())
            .and_then(|output| {
                let result: Value = serde_json::from_slice(&output.stdout)
                    .map_err(|_| "Invalid transfer response")?;
                if !output.status.success() {
                    return Err(result["error"]
                        .as_str()
                        .unwrap_or("Transfer failed")
                        .to_string());
                }
                Ok(result)
            });
        match start(resources, workspace) {
            Ok(engine) => *slot = Some(engine),
            Err(error) => {
                *state.failure.lock().map_err(|_| "Engine lock failed")? = Some(error.clone());
                return Err(error);
            }
        }
        result
    })
    .await
    .map_err(|e| e.to_string())?
}
#[tauri::command]
async fn save_credentials(
    app: tauri::AppHandle,
    state: tauri::State<'_, Runtime>,
    profile_id: String,
    values: Value,
) -> Result<(), String> {
    let snapshot = engine_call(state, "workspace.snapshot".into(), json!({})).await?;
    if !snapshot["profiles"]
        .as_array()
        .is_some_and(|rows| rows.iter().any(|p| p["id"] == profile_id))
    {
        return Err("Connection not found".into());
    }
    credentials::save(
        &app.path()
            .app_data_dir()
            .map_err(|e| e.to_string())?
            .join("default"),
        &profile_id,
        values,
    )
}
// Store only bounded technical metadata, never payloads or raw error messages.
static DIAGNOSTIC_LOCK: Mutex<()> = Mutex::new(());
#[tauri::command]
fn record_diagnostic(app: tauri::AppHandle, operation: String, code: String) -> Result<(), String> {
    if operation.len()>80 || code.len()>60 || !operation.chars().chain(code.chars()).all(|c| c.is_ascii_alphanumeric() || "._-".contains(c)) { return Err("Invalid diagnostic event".into()); }
    let _guard=DIAGNOSTIC_LOCK.lock().map_err(|_| "Log busy")?;
    let dir=app.path().app_log_dir().map_err(|e|e.to_string())?;
    std::fs::create_dir_all(&dir).map_err(|e|e.to_string())?;
    std::fs::set_permissions(&dir,std::fs::Permissions::from_mode(0o700)).map_err(|e|e.to_string())?;
    let path=dir.join("diagnostics.jsonl");
    if std::fs::metadata(&path).map(|m|m.len()>256*1024).unwrap_or(false) {
        std::fs::rename(&path,dir.join("diagnostics.previous.jsonl")).map_err(|e|e.to_string())?;
    }
    let mut file=std::fs::OpenOptions::new().create(true).append(true).open(path).map_err(|e|e.to_string())?;
    let timestamp=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs();
    writeln!(file,"{}",json!({"time":timestamp,"operation":operation,"code":code})).map_err(|e|e.to_string())
}
#[tauri::command]
fn diagnostics_report(app: tauri::AppHandle) -> Result<String,String> {
    let _guard=DIAGNOSTIC_LOCK.lock().map_err(|_| "Log busy")?;
    let path=app.path().app_log_dir().map_err(|e|e.to_string())?.join("diagnostics.jsonl");
    let logs=std::fs::read_to_string(path).unwrap_or_default();
    let recent=logs.lines().rev().take(150).collect::<Vec<_>>().into_iter().rev().collect::<Vec<_>>().join("\n");
    Ok(format!("openNews {}\nPlatform: {} / {}\nRecent technical events (Unix timestamps):\n{}",env!("CARGO_PKG_VERSION"),std::env::consts::OS,std::env::consts::ARCH,recent))
}
#[tauri::command]
fn export_diagnostics(app: tauri::AppHandle) -> Result<String,String> {
    let report=diagnostics_report(app.clone())?;
    let path=app.path().download_dir().map_err(|e|e.to_string())?.join(format!("openNews-diagnostics-{}.txt",uuid::Uuid::new_v4()));
    std::fs::write(&path,report).map_err(|e|e.to_string())?;
    Ok(path.to_string_lossy().into_owned())
}
#[tauri::command]
fn open_external(address: String) -> Result<(), String> {
    let url = url::Url::parse(&address).map_err(|_| "Invalid URL")?;
    if !matches!(url.scheme(), "https" | "http")
        || !url.username().is_empty()
        || url.password().is_some()
    {
        return Err("Unsupported URL".into());
    }
    Command::new("/usr/bin/open")
        .arg(url.as_str())
        .spawn()
        .map_err(|e| e.to_string())?;
    Ok(())
}
// Remote sites have no capability grant and cannot invoke the local engine.
#[tauri::command]
async fn open_article_site(app: tauri::AppHandle, webview: tauri::Webview, address: String, x: f64, y: f64, width: f64, height: f64) -> Result<(), String> {
    let url = url::Url::parse(&address).map_err(|_| "Invalid article URL")?;
    if !["https", "http"].contains(&url.scheme()) || url.host_str().is_none() || !url.username().is_empty() || url.password().is_some() {
        return Err("Only web article URLs are supported".into());
    }
    if ![x,y,width,height].iter().all(|v| v.is_finite() && *v >= 0.0) || width < 1.0 || height < 1.0 { return Err("Invalid browser bounds".into()); }
    let label = format!("article-site-{}", webview.window().label());
    let position = tauri::LogicalPosition::new(x, y);
    let size = tauri::LogicalSize::new(width, height);
    if let Some(site) = app.get_webview(&label) {
        site.set_position(position).map_err(|e| e.to_string())?;
        site.set_size(size).map_err(|e| e.to_string())?;
        return Ok(());
    }
    webview.window().add_child(
        tauri::webview::WebviewBuilder::new(label, tauri::WebviewUrl::External(url))
            .on_navigation(|url| ["http", "https"].contains(&url.scheme())),
        position, size,
    ).map_err(|e| e.to_string())?;
    Ok(())
}
#[tauri::command]
async fn close_article_site(app: tauri::AppHandle, webview: tauri::Webview) -> Result<(), String> {
    let label = format!("article-site-{}", webview.window().label());
    if let Some(site) = app.get_webview(&label) { site.close().map_err(|e| e.to_string())?; }
    Ok(())
}
#[tauri::command]
async fn recover_article(app: tauri::AppHandle, state: tauri::State<'_, Runtime>, article_id: String) -> Result<Value, String> {
    let socket = state.engine.lock().map_err(|_| "Engine lock failed")?.as_ref().map(|e| e.socket.clone()).ok_or("Engine unavailable")?;
    let helper = app.path().resource_dir().map_err(|e| e.to_string())?.join("runtime/public-reader");
    tauri::async_runtime::spawn_blocking(move || {
        let article = exchange(socket.clone(), "news.preview".into(), json!({"article_id":article_id}))?;
        if article["body_status"] == "full" { return Ok(article); }
        let address = article["url"].as_str().ok_or("Article URL unavailable")?;
        let output = Command::new(helper).arg(address).output().map_err(|e| e.to_string())?;
        if !output.status.success() || output.stdout.len() > 1024 * 1024 { return Ok(article); }
        let rendered: Value = serde_json::from_slice(&output.stdout).map_err(|e| e.to_string())?;
        if rendered["html"].as_str().is_some_and(|s| !s.is_empty()) {
            return exchange(socket, "news.reader.capture".into(), json!({"article_id":article_id,"html":rendered["html"]}));
        }
        Ok(article)
    }).await.map_err(|e| e.to_string())?
}
// A remaining marker means the prior process did not complete normal shutdown.
// It is deliberately called unexpected exit, not a confirmed crash.
#[derive(Default)]
struct SessionHealth { previous_unclean: bool }
#[tauri::command]
fn previous_unclean_exit(state: tauri::State<SessionHealth>) -> bool { state.previous_unclean }

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(updates::Pending::default())
        .manage(Runtime::default())
        .invoke_handler(tauri::generate_handler![
            updates::check_update,
            updates::install_update,
            engine_call,
            article_image,
            open_external,
            record_diagnostic,
            diagnostics_report,
            previous_unclean_exit,
            export_diagnostics,
            open_article_site,
            close_article_site,
            recover_article,
            save_credentials,
            device_state,
            transfer_workspace,
            export_draft
        ])
        .setup(|app| {
            let directory = app.path().app_data_dir()?;
            std::fs::create_dir_all(&directory)?;
            let marker = directory.join("session-active");
            let previous_unclean = marker.exists();
            app.manage(SessionHealth { previous_unclean });
            std::fs::write(&marker, std::process::id().to_string())?;
            if previous_unclean {
                let _ = record_diagnostic(app.handle().clone(), "app.lifecycle".into(), "UNEXPECTED_EXIT".into());
            }

            let menu = tauri::menu::Menu::with_items(
                app,
                &[
                    &tauri::menu::MenuItem::with_id(
                        app,
                        "open",
                        "Open openNews",
                        true,
                        None::<&str>,
                    )?,
                    &tauri::menu::MenuItem::with_id(
                        app,
                        "articles",
                        "Read articles",
                        true,
                        None::<&str>,
                    )?,
                    &tauri::menu::MenuItem::with_id(
                        app,
                        "reports",
                        "Daily report",
                        true,
                        None::<&str>,
                    )?,
                    &tauri::menu::MenuItem::with_id(
                        app,
                        "quit",
                        "Quit openNews",
                        true,
                        None::<&str>,
                    )?,
                ],
            )?;
            let tray = tauri::tray::TrayIconBuilder::new()
                .icon(tauri::include_image!("icons/tray.png"))
                .icon_as_template(true)
                .tooltip("openNews")
                .menu(&menu)
                .on_menu_event(|app, event| {
                    if event.id.as_ref() == "quit" {
                        app.exit(0);
                        return;
                    }
                    if event.id.as_ref() == "articles" {
                        let reader = app.get_webview_window("reader").or_else(|| {
                            tauri::WebviewWindowBuilder::new(
                                app,
                                "reader",
                                tauri::WebviewUrl::App("index.html?reader=1".into()),
                            )
                            .title("openNews · Reader")
                            .inner_size(500.0, 760.0)
                            .min_inner_size(400.0, 500.0)
                            .skip_taskbar(true)
                            .build()
                            .ok()
                        });
                        if let Some(reader) = reader {
                            let _ = reader.show();
                            let _ = reader.set_focus();
                        }
                        return;
                    }
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                    let _ = app.emit("navigate", event.id.as_ref());
                });
            tray.build(app)?;
            let handle = app.handle().clone();
            let bundled = app.path().resource_dir()?.join("runtime");
            let resources = if bundled.join("python/bin/python3.12").exists() {
                bundled
            } else if cfg!(debug_assertions) {
                PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("runtime")
            } else {
                bundled
            };
            let workspace = app.path().app_data_dir()?.join("default");
            tauri::async_runtime::spawn_blocking(move || {
                let state = handle.state::<Runtime>();
                let helper = resources.join("system-services");
                match start(resources, workspace.clone()) {
                    Ok(engine) => {
                        *state.engine.lock().unwrap() = Some(engine);
                        background(handle.clone(), helper, workspace);
                    }
                    Err(error) => *state.failure.lock().unwrap() = Some(error),
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Could not create openNews window");
    app.run(|handle, event| match event {
        tauri::RunEvent::WindowEvent {
            label,
            event: tauri::WindowEvent::CloseRequested { api, .. },
            ..
        } => {
            api.prevent_close();
            if let Some(window) = handle.get_webview_window(&label) {
                let _ = window.hide();
            }
        }
        tauri::RunEvent::Reopen { .. } => {
            if let Some(window) = handle.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }
        tauri::RunEvent::Exit => {
            if let Ok(directory) = handle.path().app_data_dir() {
                let _ = std::fs::remove_file(directory.join("session-active"));
            }

            handle
                .state::<Runtime>()
                .stopping
                .store(true, std::sync::atomic::Ordering::Relaxed);
            handle.state::<Runtime>().engine.lock().unwrap().take();
        }
        _ => {}
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn embedded_engine_keeps_data_across_restarts() {
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("runtime");
        if !root.join("python/bin/python3.12").exists() {
            panic!("Stage the embedded runtime before testing");
        }
        let workspace = tempfile::tempdir().unwrap();
        let engine = start(root.clone(), workspace.path().into()).unwrap();
        let health = exchange(engine.socket.clone(), "runtime.health".into(), json!({})).unwrap();
        assert_eq!(health["schema_version"], 1);
        assert!(health["sqlite_vec"].is_string());
        let chat = exchange(
            engine.socket.clone(),
            "chat.create".into(),
            json!({"title":"اختبار جلسة محفوظة"}),
        )
        .unwrap();
        let instructions = exchange(
            engine.socket.clone(),
            "assistant.get".into(),
            json!({"scope":"general"}),
        )
        .unwrap();
        assert!(instructions["settings"]["role"].as_str().unwrap().len() > 10);
        assert!(exchange(
            engine.socket.clone(),
            "chat.detail".into(),
            json!({"conversation_id":"invalid"})
        )
        .is_err());
        drop(engine);
        let engine = start(root, workspace.path().into()).unwrap();
        let detail = exchange(
            engine.socket.clone(),
            "chat.detail".into(),
            json!({"conversation_id":chat["conversation_id"]}),
        )
        .unwrap();
        assert_eq!(detail["title"], "اختبار جلسة محفوظة");
    }
    #[test]
    fn bridge_rejects_non_object_payload_and_oversized_frames() {
        assert!(exchange(
            PathBuf::from("/nonexistent"),
            "runtime.health".into(),
            json!(null)
        )
        .is_err());
        assert!(exchange(
            PathBuf::from("/nonexistent"),
            "runtime.health".into(),
            json!({"text":"a".repeat(MAX_FRAME)})
        )
        .unwrap_err()
        .contains("limit"));
    }
}
