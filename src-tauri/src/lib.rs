use std::sync::{Arc, Mutex};
use std::process::{Child, Command};

// 非 Windows 平台需要 Stdio
#[cfg(not(target_os = "windows"))]
use std::process::Stdio;
use tauri::{Emitter, Manager, RunEvent};
use serde::{Deserialize, Serialize};

// Windows 专用：创建新控制台窗口
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
#[cfg(target_os = "windows")]
const CREATE_NEW_CONSOLE: u32 = 0x00000010;

// ============== Python 配置 ==============

/// Python 后端配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PythonConfig {
    /// Python 解释器路径（默认 "python"）
    pub python_path: String,
    /// API 端口（默认 8009）
    pub port: u16,
    /// 监听地址（默认 "127.0.0.1"）
    pub host: String,
    /// 是否自动重启（默认 true）
    pub auto_restart: bool,
    /// 启动超时时间（毫秒，默认 10000）
    pub startup_timeout_ms: u64,
    /// 开发模式（启用热重载）
    pub dev_mode: bool,
}

impl Default for PythonConfig {
    fn default() -> Self {
        Self {
            python_path: "python".to_string(),
            port: 8009,
            host: "127.0.0.1".to_string(),
            auto_restart: true,
            startup_timeout_ms: 10000,
            dev_mode: false,
        }
    }
}

impl PythonConfig {
    /// 从配置文件加载，如果不存在则使用默认值
    pub fn load() -> Self {
        let config_paths = vec![
            "config/python.json",
            "../config/python.json",
        ];
        
        for path in config_paths {
            if let Ok(content) = std::fs::read_to_string(path) {
                if let Ok(mut config) = serde_json::from_str::<PythonConfig>(&content) {
                    println!("[tauri] Loaded Python config from {}", path);
                    if config.python_path == "python" {
                        config.python_path = detect_python_path();
                    }
                    return config;
                }
            }
        }
        
        println!("[tauri] Using default Python config");
        let mut config = Self::default();
        config.python_path = detect_python_path();
        config
    }
}

/// 检测可用的 Python 解释器路径
fn detect_python_path() -> String {
    #[cfg(target_os = "windows")]
    let candidates = vec![
        "../src-python/.venv/Scripts/python.exe",
        ".venv\\Scripts\\python.exe",
        "python",
        "python3",
    ];
    
    #[cfg(not(target_os = "windows"))]
    let candidates = vec![
        "../src-python/.venv/bin/python",
        ".venv/bin/python",
        "python3",
        "python",
    ];
    
    for candidate in candidates {
        let result = Command::new(candidate)
            .args(["--version"])
            .output();
        
        if let Ok(output) = result {
            if output.status.success() {
                let version = String::from_utf8_lossy(&output.stdout);
                println!("[tauri] Found Python at '{}': {}", candidate, version.trim());
                return candidate.to_string();
            }
        }
    }
    
    println!("[tauri] No Python found, using default 'python'");
    "python".to_string()
}

/// 检查 aestiv 包是否已安装
fn check_aestiv_installed(python_path: &str) -> bool {
    let result = Command::new(python_path)
        .args(["-c", "import aestiv; print('ok')"])
        .output();
    
    if let Ok(output) = result {
        if output.status.success() {
            println!("[tauri] aestiv package is installed");
            return true;
        }
    }
    
    println!("[tauri] aestiv package is NOT installed");
    false
}

/// 检查 Python 是否可用
fn is_python_available(python_path: &str) -> bool {
    Command::new(python_path)
        .args(["--version"])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

// ============== Python 进程管理 ==============

/// Python 后端进程包装器
struct PythonProcess {
    process: Option<Child>,
    config: PythonConfig,
}

impl PythonProcess {
    fn new(config: PythonConfig) -> Self {
        Self { process: None, config }
    }
    
    fn set_process(&mut self, process: Child) {
        self.process = Some(process);
    }
    
    fn take_process(&mut self) -> Option<Child> {
        self.process.take()
    }
    
    fn has_process(&self) -> bool {
        self.process.is_some()
    }
    
    fn config(&self) -> &PythonConfig {
        &self.config
    }
}

impl Drop for PythonProcess {
    fn drop(&mut self) {
        if let Some(mut process) = self.process.take() {
            println!("[tauri] PythonProcess dropping, killing process...");
            let _ = process.kill();
        }
    }
}

// ============== 进程清理 ==============

fn cleanup_python_process(app_handle: &tauri::AppHandle) {
    println!("[tauri] Cleaning up Python backend process...");
    if let Some(state) = app_handle.try_state::<Arc<Mutex<PythonProcess>>>() {
        if let Ok(mut child) = state.lock() {
            if let Some(mut process) = child.take_process() {
                println!("[tauri] Killing Python process...");
                let _ = process.kill();
                let _ = process.wait();
                println!("[tauri] Python process terminated.");
            }
        }
    }
    
    // 额外清理端口
    cleanup_python_ports();
}

fn cleanup_python_ports() {
    let ports = [8008, 8009, 8010, 8011, 8012];
    
    #[cfg(target_os = "windows")]
    for port in ports {
        let _ = Command::new("cmd")
            .args(["/C", &format!(
                "for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{} ^| findstr LISTENING') do taskkill /F /PID %a 2>nul",
                port
            )])
            .output();
    }
    
    #[cfg(not(target_os = "windows"))]
    for port in ports {
        if let Ok(output) = Command::new("lsof").args(["-ti", &format!(":{}", port)]).output() {
            let pids = String::from_utf8_lossy(&output.stdout);
            for pid in pids.trim().split('\n').filter(|s| !s.is_empty()) {
                let _ = Command::new("kill").args(["-9", pid]).output();
            }
        }
    }
}

// ============== Tauri 命令 ==============

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn toggle_fullscreen(window: tauri::Window) {
    if let Ok(is_fullscreen) = window.is_fullscreen() {
        let _ = window.set_fullscreen(!is_fullscreen);
    }
}

/// 启动 Python 后端进程
fn spawn_python_backend(app_handle: tauri::AppHandle) -> Result<(), String> {
    let config = if let Some(state) = app_handle.try_state::<Arc<Mutex<PythonProcess>>>() {
        let process_state = state.lock().unwrap();
        if process_state.has_process() {
            println!("[tauri] Python backend is already running.");
            return Ok(());
        }
        process_state.config().clone()
    } else {
        return Err("Failed to access app state".to_string());
    };

    println!("[tauri] Starting Python backend with config: {:?}", config);
    
    if !is_python_available(&config.python_path) {
        let msg = format!("Python not found at '{}'.", config.python_path);
        println!("[tauri] Error: {}", msg);
        let _ = app_handle.emit("python-error", msg.clone());
        return Err(msg);
    }
    
    if !check_aestiv_installed(&config.python_path) {
        let msg = "aestiv package not found. Run: pip install -e ./src-python".to_string();
        println!("[tauri] Error: {}", msg);
        let _ = app_handle.emit("python-error", msg.clone());
        return Err(msg);
    }
    
    // 构建启动参数
    let mut args = vec!["-m", "aestiv"];
    if config.dev_mode {
        args.push("--standalone");
    }
    
    println!("[tauri] Spawning: {} {:?}", config.python_path, args);
    
    // 使用 Windows Terminal + PowerShell 启动 Python（方便查看日志）
    #[cfg(target_os = "windows")]
    let child = {
        // 构建 PowerShell 命令（使用 & 调用带空格路径的程序）
        let python_cmd = format!("& '{}' {}", config.python_path, args.join(" "));
        
        // 尝试使用 Windows Terminal (wt.exe) + pwsh
        Command::new("wt.exe")
            .args(["--title", "Aestivus Python Backend", "pwsh", "-NoExit", "-Command", &python_cmd])
            .spawn()
            .or_else(|_| {
                // 回退：直接用 pwsh 打开新窗口
                println!("[tauri] Windows Terminal not found, using pwsh...");
                Command::new("pwsh")
                    .args(["-NoExit", "-Command", &python_cmd])
                    .creation_flags(CREATE_NEW_CONSOLE)
                    .spawn()
            })
            .map_err(|e| {
                let msg = format!("Failed to spawn Python: {}", e);
                println!("[tauri] {}", msg);
                let _ = app_handle.emit("python-error", msg.clone());
                msg
            })?
    };
    
    #[cfg(not(target_os = "windows"))]
    let child = {
        // macOS/Linux: 使用终端模拟器打开
        let terminal_cmd = if cfg!(target_os = "macos") {
            format!("osascript -e 'tell app \"Terminal\" to do script \"{} {}\"'", 
                config.python_path, args.join(" "))
        } else {
            // Linux: 尝试常见的终端模拟器
            format!("x-terminal-emulator -e {} {}", config.python_path, args.join(" "))
        };
        
        Command::new("sh")
            .args(["-c", &terminal_cmd])
            .spawn()
            .or_else(|_| {
                // 回退：直接启动（无可见终端）
                Command::new(&config.python_path)
                    .args(&args)
                    .stdout(Stdio::piped())
                    .stderr(Stdio::piped())
                    .spawn()
            })
            .map_err(|e| {
                let msg = format!("Failed to spawn Python: {}", e);
                println!("[tauri] {}", msg);
                let _ = app_handle.emit("python-error", msg.clone());
                msg
            })?
    };
    
    let pid = child.id();
    println!("[tauri] Python process spawned with PID: {} (in new console window)", pid);
    
    // 存储进程
    if let Some(state) = app_handle.try_state::<Arc<Mutex<PythonProcess>>>() {
        state.lock().unwrap().set_process(child);
    }

    Ok(())
}



#[tauri::command]
fn shutdown_python(app_handle: tauri::AppHandle) -> Result<String, String> {
    println!("[tauri] Shutting down Python backend...");
    cleanup_python_process(&app_handle);
    Ok("Python backend shutdown.".to_string())
}

#[tauri::command]
fn start_python(app_handle: tauri::AppHandle) -> Result<String, String> {
    println!("[tauri] Starting Python backend...");
    spawn_python_backend(app_handle)?;
    Ok("Python backend started.".to_string())
}

#[tauri::command]
fn get_python_config(app_handle: tauri::AppHandle) -> Result<PythonConfig, String> {
    if let Some(state) = app_handle.try_state::<Arc<Mutex<PythonProcess>>>() {
        let guard = state.lock().map_err(|_| "Lock failed")?;
        Ok(guard.config().clone())
    } else {
        Err("State not found".to_string())
    }
}

// 兼容旧 API
#[tauri::command]
fn shutdown_sidecar(app_handle: tauri::AppHandle) -> Result<String, String> {
    shutdown_python(app_handle)
}

#[tauri::command]
fn start_sidecar(app_handle: tauri::AppHandle) -> Result<String, String> {
    start_python(app_handle)
}

// ============== 应用入口 ==============

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let config = PythonConfig::load();
    
    tauri::Builder::default()
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .setup(move |app| {
            app.manage(Arc::new(Mutex::new(PythonProcess::new(config.clone()))));
            
            let app_handle = app.handle().clone();
            if let Some(window) = app.get_webview_window("main") {
                window.on_window_event(move |event| {
                    if matches!(event, tauri::WindowEvent::CloseRequested { .. } | tauri::WindowEvent::Destroyed) {
                        println!("[tauri] Window closing, cleanup...");
                        cleanup_python_process(&app_handle);
                    }
                });
            }
            
            // 启动 Python 后端
            let app_handle = app.handle().clone();
            println!("[tauri] Starting Python backend...");
            if let Err(e) = spawn_python_backend(app_handle) {
                eprintln!("[tauri] Failed to start Python backend: {}", e);
            }
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            start_python,
            shutdown_python,
            start_sidecar,
            shutdown_sidecar,
            toggle_fullscreen,
            get_python_config
        ])
        .build(tauri::generate_context!())
        .expect("Error building tauri application")
        .run(|app_handle, event| {
            if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
                println!("[tauri] App exiting, cleanup...");
                cleanup_python_process(&app_handle);
            }
        });
}
