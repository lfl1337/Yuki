use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::process::CommandChild;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::ShellExt;

#[cfg(not(debug_assertions))]
use std::fs::OpenOptions;
use std::io::Write;
#[cfg(not(debug_assertions))]
use std::sync::Arc;

struct BackendProcess(Mutex<Option<CommandChild>>);

struct DiscoveredPort(Mutex<Option<String>>);

#[tauri::command]
fn get_backend_port(state: tauri::State<DiscoveredPort>) -> Option<String> {
    state.0.lock().unwrap().clone()
}

fn get_runtime_port_path(_app: &AppHandle) -> PathBuf {
    // Always use %APPDATA%\Yuki\.runtime_port — matches run.py's fixed write location.
    let appdata = std::env::var("APPDATA").unwrap_or_default();
    PathBuf::from(&appdata).join("Yuki").join(".runtime_port")
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess(Mutex::new(None)))
        .manage(DiscoveredPort(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .setup(|app| {
            let app_handle = app.handle().clone();
            let runtime_port_path = get_runtime_port_path(&app_handle);

            #[cfg(not(debug_assertions))]
            {
                // --- Production: spawn Python sidecar ---
                // Use %APPDATA%\Yuki — same location Python uses for all data.
                // app_data_dir() resolves to %APPDATA%\app.yuki.media which may not exist.
                let data_dir = {
                    let appdata = std::env::var("APPDATA").unwrap_or_default();
                    let d = if appdata.is_empty() {
                        PathBuf::from(".")
                    } else {
                        PathBuf::from(&appdata).join("Yuki")
                    };
                    let _ = std::fs::create_dir_all(&d);
                    d
                };
                let data_dir_str = data_dir.to_string_lossy().to_string();

                // Kill any leftover backend from a previous crashed session.
                let _ = std::process::Command::new("taskkill")
                    .args(["/f", "/im", "yuki-backend-x86_64-pc-windows-msvc.exe"])
                    .output();

                // Delete stale .runtime_port so the poll below waits for the
                // freshly-started backend rather than picking up an old value.
                let _ = std::fs::remove_file(&runtime_port_path);

                // Open log file
                let log_path = data_dir.join("yuki-tauri.log");
                let log_file = Arc::new(Mutex::new(
                    OpenOptions::new()
                        .create(true)
                        .append(true)
                        .open(&log_path)
                        .ok(),
                ));

                let ah_for_error = app_handle.clone();

                let sidecar_cmd = match app_handle.shell().sidecar("yuki-backend") {
                    Ok(cmd) => cmd,
                    Err(e) => {
                        let _ = ah_for_error.emit("backend-error", format!("Sidecar not found: {e}"));
                        return Ok(());
                    }
                };
                let (mut rx, child) = match sidecar_cmd.args(["--data-dir", &data_dir_str]).spawn() {
                    Ok(pair) => pair,
                    Err(e) => {
                        let _ = ah_for_error.emit("backend-error", format!("Spawn failed: {e}"));
                        return Ok(());
                    }
                };

                *app_handle.state::<BackendProcess>().0.lock().unwrap() = Some(child);

                // Stream sidecar output to log
                let log_clone = Arc::clone(&log_file);
                tauri::async_runtime::spawn(async move {
                    use tauri_plugin_shell::process::CommandEvent;
                    while let Some(event) = rx.recv().await {
                        let line = match event {
                            CommandEvent::Stdout(b) => String::from_utf8_lossy(&b).to_string(),
                            CommandEvent::Stderr(b) => String::from_utf8_lossy(&b).to_string(),
                            _ => continue,
                        };
                        if let Some(ref mut f) = *log_clone.lock().unwrap() {
                            let _ = writeln!(f, "{}", line.trim());
                        }
                    }
                });
            }

            // Health-check thread: poll .runtime_port for up to 15s (150×100ms),
            // then emit the discovered port + ready signal to the frontend.
            let rp = runtime_port_path.clone();
            let ah = app_handle.clone();

            #[cfg(not(debug_assertions))]
            let data_dir_for_log_opt: Option<PathBuf> = {
                let appdata = std::env::var("APPDATA").unwrap_or_default();
                if appdata.is_empty() { None } else {
                    let d = PathBuf::from(&appdata).join("Yuki");
                    let _ = std::fs::create_dir_all(&d);
                    Some(d)
                }
            };
            #[cfg(debug_assertions)]
            let data_dir_for_log_opt: Option<PathBuf> = None;

            std::thread::spawn(move || {
                let write_log = |msg: &str| {
                    if let Some(ref d) = data_dir_for_log_opt {
                        if let Ok(mut f) = std::fs::OpenOptions::new()
                            .create(true).append(true)
                            .open(d.join("yuki-tauri.log")) {
                            let _ = writeln!(f, "[Tauri] {}", msg);
                        }
                    }
                };

                write_log(&format!("Polling for port file: {:?}", rp));

                for _ in 0..150 {
                    std::thread::sleep(Duration::from_millis(100));
                    if rp.exists() {
                        if let Ok(content) = std::fs::read_to_string(&rp) {
                            let trimmed = content.trim().to_string();
                            if trimmed.parse::<u16>().is_ok() {
                                write_log(&format!("Port found: {}", trimmed));
                                // Store for invoke-based discovery (race-condition-free)
                                *ah.state::<DiscoveredPort>().0.lock().unwrap() = Some(trimmed.clone());
                                // Also emit as secondary mechanism
                                let _ = ah.emit("backend-port", &trimmed);
                                // Verify backend is actually listening before signalling ready
                                let url = format!("http://127.0.0.1:{}/health", trimmed);
                                for _ in 0..30 {
                                    if let Ok(resp) = ureq::get(&url).call() {
                                        if resp.status() == 200 {
                                            write_log("Health check passed — backend ready");
                                            let _ = ah.emit("backend-ready", ());
                                            return;
                                        }
                                    }
                                    std::thread::sleep(Duration::from_millis(500));
                                }
                                write_log("Health check timed out — signalling ready anyway");
                                let _ = ah.emit("backend-ready", ());
                                return;
                            }
                        }
                    }
                }
                // Timeout: fall back so UI doesn't hang forever
                write_log("Timeout: port file not found after 15s, using 9001");
                let _ = ah.emit("backend-port", "9001".to_string());
                let _ = ah.emit("backend-ready", ());
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Kill tracked sidecar child process
                if let Some(child) = window
                    .app_handle()
                    .state::<BackendProcess>()
                    .0
                    .lock()
                    .unwrap()
                    .take()
                {
                    let _ = child.kill();
                }
                // Taskkill as backup — production only, no console window
                #[cfg(all(not(debug_assertions), target_os = "windows"))]
                {
                    use std::os::windows::process::CommandExt;
                    let _ = std::process::Command::new("taskkill")
                        .args(["/f", "/im", "yuki-backend-x86_64-pc-windows-msvc.exe"])
                        .creation_flags(0x08000000)
                        .stdout(std::process::Stdio::null())
                        .stderr(std::process::Stdio::null())
                        .spawn();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Yuki");
}
