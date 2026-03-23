use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::process::CommandChild;
#[cfg(not(debug_assertions))]
use tauri_plugin_shell::ShellExt;

#[cfg(not(debug_assertions))]
use std::fs::OpenOptions;
#[cfg(not(debug_assertions))]
use std::io::Write;
#[cfg(not(debug_assertions))]
use std::sync::Arc;

struct BackendProcess(Mutex<Option<CommandChild>>);

#[allow(unused_variables)]
fn get_runtime_port_path(app: &AppHandle) -> PathBuf {
    // In dev: read from backend/.runtime_port relative to project root
    // In release: read from sidecar working dir (AppData/Yuki)
    #[cfg(debug_assertions)]
    {
        // project_root/backend/.runtime_port
        let exe = std::env::current_exe().unwrap_or_default();
        let project_root = exe
            .parent() // target/debug
            .and_then(|p| p.parent()) // target
            .and_then(|p| p.parent()) // frontend
            .and_then(|p| p.parent()) // yuki root
            .unwrap_or(&PathBuf::from("."))
            .to_path_buf();
        project_root.join("backend").join(".runtime_port")
    }
    #[cfg(not(debug_assertions))]
    {
        let data_dir = app
            .path()
            .app_data_dir()
            .unwrap_or_else(|_| PathBuf::from("."));
        // .runtime_port is written next to the sidecar binary
        // The sidecar writes it in its working dir (AppData/Yuki)
        data_dir.join(".runtime_port")
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            let app_handle = app.handle().clone();
            let runtime_port_path = get_runtime_port_path(&app_handle);

            #[cfg(not(debug_assertions))]
            {
                // --- Production: spawn Python sidecar ---
                let data_dir = app
                    .path()
                    .app_data_dir()
                    .unwrap_or_else(|_| PathBuf::from("."));
                let data_dir_str = data_dir.to_string_lossy().to_string();

                // Open log file
                let log_path = data_dir.join("yuki-tauri.log");
                let log_file = Arc::new(Mutex::new(
                    OpenOptions::new()
                        .create(true)
                        .append(true)
                        .open(&log_path)
                        .ok(),
                ));

                let (mut rx, child) = app_handle
                    .shell()
                    .sidecar("yuki-backend")
                    .expect("yuki-backend sidecar not found")
                    .args(["--data-dir", &data_dir_str])
                    .spawn()
                    .expect("Failed to spawn yuki-backend");

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

            // Health-check thread: poll .runtime_port for up to 10s
            let rp = runtime_port_path.clone();
            let ah = app_handle.clone();
            std::thread::spawn(move || {
                for _ in 0..20 {
                    std::thread::sleep(Duration::from_millis(500));
                    if rp.exists() {
                        let _ = ah.emit("backend-ready", ());
                        return;
                    }
                }
                // Timeout: emit anyway so the UI doesn't hang forever
                let _ = ah.emit("backend-ready", ());
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill backend on window close
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
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Yuki");
}
