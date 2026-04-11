// Aiko Desktop — Tauri Core v7 (window controls + proactive + TTS fix)
// ═══════════════════════════════════════════════════════════
// Manages the entire Aiko ecosystem from Rust for 7x faster startup

mod process_manager;

use tauri::{Manager, Listener};
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use window_vibrancy::apply_mica;
use tauri_plugin_global_shortcut::ShortcutState;
use std::path::PathBuf;
use std::sync::Arc;

use process_manager::ProcessManager;

// ── Tauri Commands ─────────────────────────────────────────────

#[tauri::command]
fn minimize_window(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.minimize();
    }
}

#[tauri::command]
fn maximize_window(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        if win.is_maximized().unwrap_or(false) {
            let _ = win.unmaximize();
        } else {
            let _ = win.maximize();
        }
    }
}

#[tauri::command]
fn close_window(app: tauri::AppHandle) {
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.close();
    }
}

#[tauri::command]
fn log_error(app: tauri::AppHandle, message: String, stack: String) {
    if let Ok(path) = app.path().app_log_dir() {
        std::fs::create_dir_all(&path).ok();
        let log_path = path.join("error.log");
        let content = format!("{}\n{}\n\n", message, stack);
        use std::io::Write;
        if let Ok(mut file) = std::fs::OpenOptions::new()
            .create(true).append(true).open(log_path) {
            file.write_all(content.as_bytes()).ok();
        }
    }
}

/// Called by frontend to check if the Neural Hub is alive
#[tauri::command]
async fn check_hub_status() -> Result<bool, String> {
    Ok(process_manager::check_hub_health("127.0.0.1", 8080).await)
}

/// Called by frontend to get startup progress
#[tauri::command]
async fn get_startup_status() -> Result<String, String> {
    if process_manager::check_hub_health("127.0.0.1", 8080).await {
        Ok("online".to_string())
    } else {
        Ok("starting".to_string())
    }
}

/// Get status of all managed processes
#[tauri::command]
async fn get_process_status(pm: tauri::State<'_, Arc<ProcessManager>>) -> Result<Vec<process_manager::ProcessStatusDto>, String> {
    Ok(pm.get_process_status())
}

// ── Resolve the Aiko project root ──────────────────────────────

fn find_project_root() -> Option<PathBuf> {
    // Priority 1: Current directory (or walk up)
    if let Ok(cwd) = std::env::current_dir() {
        let mut dir = Some(cwd);
        for _ in 0..4 {
            if let Some(ref d) = dir {
                if d.join("core").join("neural_hub.py").exists() {
                    return Some(d.clone());
                }
                dir = d.parent().map(|p| p.to_path_buf());
            }
        }
    }

    // Priority 2: Relative to executable (for production builds)
    if let Ok(exe) = std::env::current_exe() {
        // In Tauri dev: exe is in target/debug
        // Walk up until we find core/neural_hub.py
        let mut dir = exe.parent().map(|p| p.to_path_buf());
        for _ in 0..6 {
            if let Some(ref d) = dir {
                if d.join("core").join("neural_hub.py").exists() {
                    return Some(d.clone());
                }
                dir = d.parent().map(|p| p.to_path_buf());
            }
        }
    }

    None
}

// ── Main Entry Point ───────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_autostart::init(tauri_plugin_autostart::MacosLauncher::LaunchAgent, Some(vec!["--start-hidden"])))
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            log_error, minimize_window, maximize_window, close_window,
            check_hub_status, get_startup_status, get_process_status
        ])
        .setup(|app| {
            // ══════════════════════════════════════════════════════════
            //  RUST PROCESS MANAGER — Full ecosystem startup
            // ══════════════════════════════════════════════════════════
            if let Some(project_root) = find_project_root() {
                println!("[Aiko/Rust] Project root: {:?}", project_root);

                let pm = Arc::new(ProcessManager::new(project_root));

                // Store ProcessManager in Tauri state for commands
                app.manage(pm.clone());

                // Step 1: Check if Hub is already alive (launched by AikoLauncher.py)
                let hub_already_alive = {
                    let rt = tokio::runtime::Runtime::new().unwrap();
                    rt.block_on(async {
                        process_manager::check_hub_health("127.0.0.1", 8080).await
                    })
                };

                if hub_already_alive {
                    println!("[Aiko/Rust] Neural Hub already online — skipping process startup");

                    // Still start monitoring in background
                    let pm_monitor = pm.clone();
                    std::thread::spawn(move || {
                        let rt = tokio::runtime::Runtime::new().unwrap();
                        rt.block_on(async {
                            println!("[Aiko/Rust] ALL SYSTEMS GO (external launcher mode)");
                        });
                    });
                } else {

                    // Step 2: Kill stale processes (only when we need to do a cold start)
                    println!("[Aiko/Rust] Cleaning stale processes...");
                    pm.cleanup_stale_processes();

                    // Step 3: Start Ollama
                    println!("[Aiko/Rust] Starting Ollama...");
                    pm.start_ollama();

                    // Step 4: Start Neural Hub
                    println!("[Aiko/Rust] Starting Neural Hub...");
                    match pm.start_hub() {
                        Ok(_) => println!("[Aiko/Rust] Neural Hub spawned"),
                        Err(e) => eprintln!("[Aiko/Rust] Hub error: {}", e),
                    }

                    // Step 5: Wait for hub in background, then start bots
                    let pm_async = pm.clone();
                    std::thread::spawn(move || {
                        let rt = tokio::runtime::Runtime::new().unwrap();
                        rt.block_on(async {
                            println!("[Aiko/Rust] Waiting for Neural Hub health...");
                            let ready = process_manager::wait_for_hub("127.0.0.1", 8080, 150).await;
                            if ready {
                                println!("[Aiko/Rust] Neural Hub ONLINE — starting satellites");
                                pm_async.start_bridge();
                                tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                                pm_async.start_bots();
                                println!("[Aiko/Rust] ALL SYSTEMS GO");

                                let pm_monitor = pm_async.clone();
                                tokio::spawn(async move {
                                    pm_monitor.start_monitoring().await;
                                });
                            } else {
                                eprintln!("[Aiko/Rust] CRITICAL: Hub failed to start after 30s");
                            }
                        });
                    });
                }

                // Store PM for cleanup on exit
                let pm_exit = pm.clone();
                if let Some(win) = app.get_webview_window("main") {
                    win.on_window_event(move |event| {
                        if let tauri::WindowEvent::Destroyed = event {
                            println!("[Aiko/Rust] Shutting down all processes...");
                            pm_exit.shutdown();
                        }
                    });
                }
            } else {
                eprintln!("[Aiko/Rust] WARNING: Could not find project root!");
            }

            // ══════════════════════════════════════════════════════════
            //  TRAY + SHORTCUTS + VISUAL EFFECTS
            // ══════════════════════════════════════════════════════════
            let show_i = MenuItem::with_id(app, "show", "Show Aiko", true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show_i, &quit_i])?;
            
            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => { 
                        if let Some(win) = app.get_webview_window("main") {
                            win.show().unwrap(); 
                            win.set_focus().unwrap();
                        }
                    }
                    "quit" => { app.exit(0); }
                    _ => {}
                })
                .build(app)?;

            // Global Shortcut: Ctrl+Shift+A to toggle visibility
            app.handle().plugin(
              tauri_plugin_global_shortcut::Builder::new()
                .with_shortcut("ctrl+shift+a")?
                .with_handler(|app, _shortcut, event| {
                  if event.state == ShortcutState::Pressed {
                    if let Some(win) = app.get_webview_window("main") {
                        if win.is_visible().unwrap() {
                            win.hide().unwrap();
                        } else {
                            win.show().unwrap();
                            win.set_focus().unwrap();
                        }
                    }
                  }
                })
                .build()
            )?;

            // Visual Effects & Boot Logic
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_decorations(false);
                let _ = window.set_shadow(true);

                #[cfg(target_os = "windows")]
                {
                    let _ = apply_mica(&window, Some(true));
                }

                // Listen for app-ready from frontend
                let win_clone = window.clone();
                app.listen("app-ready", move |_| {
                    let _ = win_clone.show();
                    let _ = win_clone.set_focus();
                });

                // Fallback: show window after 3s
                let win_fallback = window.clone();
                std::thread::spawn(move || {
                    std::thread::sleep(std::time::Duration::from_millis(3000));
                    let _ = win_fallback.show();
                    let _ = win_fallback.set_focus();
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
