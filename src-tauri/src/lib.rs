use std::sync::{Arc, Mutex};
use tauri::{Emitter, Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use serde::{Deserialize, Serialize};

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
        // 尝试从多个位置加载配置
        let config_paths = vec![
            "config/python.json",
            "../config/python.json",
        ];
        
        for path in config_paths {
            if let Ok(content) = std::fs::read_to_string(path) {
                if let Ok(mut config) = serde_json::from_str::<PythonConfig>(&content) {
                    println!("[tauri] Loaded Python config from {}", path);
                    // 自动检测 Python 路径（如果配置为默认值）
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
/// 优先级：项目 venv > 系统 Python
fn detect_python_path() -> String {
    use std::process::Command;
    
    // 候选路径列表（按优先级排序）
    #[cfg(target_os = "windows")]
    let candidates = vec![
        ".venv\\Scripts\\python.exe",
        "src-python\\.venv\\Scripts\\python.exe",
        "../src-python/.venv/Scripts/python.exe",
        "python",
        "python3",
    ];
    
    #[cfg(not(target_os = "windows"))]
    let candidates = vec![
        ".venv/bin/python",
        "src-python/.venv/bin/python",
        "../src-python/.venv/bin/python",
        "python3",
        "python",
    ];
    
    for candidate in candidates {
        // 检查是否可执行
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
    
    // 默认返回 python
    println!("[tauri] No Python found, using default 'python'");
    "python".to_string()
}

/// 检查 aestival-backend 包是否已安装
fn check_aestival_backend_installed(python_path: &str) -> bool {
    use std::process::Command;
    
    let result = Command::new(python_path)
        .args(["-c", "import aestival_backend; print('ok')"])
        .output();
    
    if let Ok(output) = result {
        if output.status.success() {
            println!("[tauri] aestival-backend package is installed");
            return true;
        }
    }
    
    println!("[tauri] aestival-backend package is NOT installed");
    false
}

/// 检查 Python 是否可用
fn is_python_available(python_path: &str) -> bool {
    use std::process::Command;
    
    let result = Command::new(python_path)
        .args(["--version"])
        .output();
    
    if let Ok(output) = result {
        if output.status.success() {
            return true;
        }
    }
    
    false
}

// ============== Python 进程管理 ==============

/// Python 后端进程包装器
struct PythonProcess {
    process: Option<CommandChild>,
    config: PythonConfig,
}

impl PythonProcess {
    fn new(config: PythonConfig) -> Self {
        Self { 
            process: None,
            config,
        }
    }
    
    fn set_process(&mut self, process: CommandChild) {
        self.process = Some(process);
    }
    
    fn take_process(&mut self) -> Option<CommandChild> {
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
        if let Some(process) = self.process.take() {
            println!("[tauri] PythonProcess dropping, killing process...");
            let _ = process.kill();
        }
    }
}

// ============== 进程清理 ==============

/// 清理 Python 后端进程
fn cleanup_python_process(app_handle: &tauri::AppHandle) {
    println!("[tauri] Cleaning up Python backend process...");
    if let Some(child_process) = app_handle.try_state::<Arc<Mutex<PythonProcess>>>() {
        if let Ok(mut child) = child_process.lock() {
            if let Some(mut process) = child.take_process() {
                // 尝试优雅关闭
                let command = "sidecar shutdown\n";
                let buf: &[u8] = command.as_bytes();
                if let Err(e) = process.write(buf) {
                    println!("[tauri] Failed to send shutdown command: {}", e);
                } else {
                    println!("[tauri] Sent graceful shutdown command.");
                    std::thread::sleep(std::time::Duration::from_millis(500));
                }

                // 强制终止进程
                match process.kill() {
                    Ok(_) => {
                        println!("[tauri] Python process terminated successfully.");
                        std::thread::sleep(std::time::Duration::from_millis(200));
                    },
                    Err(e) => println!("[tauri] Failed to kill process (may already be dead): {}", e),
                }
            } else {
                println!("[tauri] No Python process found to cleanup.");
            }
        } else {
            println!("[tauri] Failed to acquire lock on process state.");
        }
    } else {
        println!("[tauri] Python process state not found.");
    }
    
    // 额外清理：终止占用端口的进程
    println!("[tauri] Performing additional port cleanup...");
    cleanup_python_ports();
}

/// 清理占用端口的进程（跨平台）
fn cleanup_python_ports() {
    let ports = [8008, 8009, 8010, 8011, 8012];
    
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        for port in ports {
            // Windows: 使用 netstat + taskkill
            if let Ok(output) = Command::new("cmd")
                .args(["/C", &format!("for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{} ^| findstr LISTENING') do @echo %a", port)])
                .output()
            {
                let pids_str = String::from_utf8_lossy(&output.stdout);
                for pid in pids_str.trim().split_whitespace() {
                    if let Ok(pid_num) = pid.parse::<u32>() {
                        if pid_num > 0 {
                            println!("[tauri] Killing process {} on port {}", pid_num, port);
                            let _ = Command::new("taskkill")
                                .args(["/F", "/PID", &pid_num.to_string()])
                                .output();
                        }
                    }
                }
            }
        }
    }
    
    #[cfg(not(target_os = "windows"))]
    {
        use std::process::Command;
        for port in ports {
            // Unix: 使用 lsof
            if let Ok(output) = Command::new("lsof")
                .args(["-ti", &format!(":{}", port)])
                .output()
            {
                let pids_str = String::from_utf8_lossy(&output.stdout);
                let pids: Vec<&str> = pids_str.trim().split('\n').filter(|s| !s.is_empty()).collect();
                
                for pid in pids {
                    if let Ok(pid_num) = pid.parse::<u32>() {
                        println!("[tauri] Killing process {} on port {}", pid_num, port);
                        let _ = Command::new("kill")
                            .args(["-9", &pid_num.to_string()])
                            .output();
                    }
                }
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
        window.set_fullscreen(!is_fullscreen).unwrap();
    }
}

/// 启动 Python 后端进程
fn spawn_python_backend(app_handle: tauri::AppHandle) -> Result<(), String> {
    // 检查是否已有进程在运行
    let config = if let Some(state) = app_handle.try_state::<Arc<Mutex<PythonProcess>>>() {
        let process_state = state.lock().unwrap();
        if process_state.has_process() {
            println!("[tauri] Python backend is already running. Skipping spawn.");
            return Ok(());
        }
        process_state.config().clone()
    } else {
        return Err("Failed to access app state".to_string());
    };

    println!("[tauri] Starting Python backend with config: {:?}", config);
    
    // 检查 Python 是否可用
    if !is_python_available(&config.python_path) {
        let error_msg = format!(
            "Python not found at '{}'. Please install Python and ensure it's in your PATH.",
            config.python_path
        );
        println!("[tauri] Error: {}", error_msg);
        // 发送错误事件到前端
        let _ = app_handle.emit("python-error", error_msg.clone());
        return Err(error_msg);
    }
    
    // 检查 aestival-backend 包是否已安装
    if !check_aestival_backend_installed(&config.python_path) {
        let error_msg = format!(
            "aestival-backend package not found. Please install it with:\n  pip install aestival-backend\nor for development:\n  pip install -e ./src-python"
        );
        println!("[tauri] Error: {}", error_msg);
        let _ = app_handle.emit("python-error", error_msg.clone());
        return Err(error_msg);
    }
    
    // 构建启动参数
    let mut args = vec!["-m".to_string(), "aestival_backend".to_string()];
    
    // 开发模式添加 --standalone 参数
    if config.dev_mode {
        args.push("--standalone".to_string());
    }
    
    // 使用 shell 命令启动 Python 包
    let shell = app_handle.shell();
    let command = shell
        .command(&config.python_path)
        .args(&args);
    
    let (mut rx, child) = command.spawn().map_err(|e| {
        let error_msg = format!("Failed to spawn Python backend: {}. Make sure Python is installed and aestival-backend package is available.", e);
        let _ = app_handle.emit("python-error", error_msg.clone());
        error_msg
    })?;
    
    // 存储进程
    if let Some(state) = app_handle.try_state::<Arc<Mutex<PythonProcess>>>() {
        state.lock().unwrap().set_process(child);
    } else {
        return Err("Failed to access app state".to_string());
    }

    // 异步监控进程输出
    let app_handle_for_restart = app_handle.clone();
    tauri::async_runtime::spawn(async move {
        let mut restart_count = 0;
        const MAX_RESTARTS: u32 = 3;
        
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line_bytes) => {
                    let line = String::from_utf8_lossy(&line_bytes);
                    println!("Python stdout: {}", line);
                    app_handle
                        .emit("python-stdout", line.to_string())
                        .expect("Failed to emit python stdout event");
                }
                CommandEvent::Stderr(line_bytes) => {
                    let line = String::from_utf8_lossy(&line_bytes);
                    eprintln!("Python stderr: {}", line);
                    app_handle
                        .emit("python-stderr", line.to_string())
                        .expect("Failed to emit python stderr event");
                }
                CommandEvent::Terminated(payload) => {
                    println!("[tauri] Python process terminated: {:?}", payload);
                    app_handle
                        .emit("python-terminated", format!("{:?}", payload))
                        .expect("Failed to emit python terminated event");
                    
                    // 检查是否需要自动重启
                    let should_restart = if let Some(state) = app_handle_for_restart.try_state::<Arc<Mutex<PythonProcess>>>() {
                        if let Ok(mut process_state) = state.lock() {
                            // 清除旧进程引用
                            process_state.take_process();
                            process_state.config().auto_restart && restart_count < MAX_RESTARTS
                        } else {
                            false
                        }
                    } else {
                        false
                    };
                    
                    if should_restart {
                        restart_count += 1;
                        println!("[tauri] Auto-restarting Python backend (attempt {}/{})", restart_count, MAX_RESTARTS);
                        
                        // 等待一小段时间再重启
                        tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;
                        
                        if let Err(e) = spawn_python_backend(app_handle_for_restart.clone()) {
                            println!("[tauri] Failed to restart Python backend: {}", e);
                            let _ = app_handle_for_restart.emit("python-error", format!("Failed to restart: {}", e));
                        }
                    } else if restart_count >= MAX_RESTARTS {
                        let msg = format!("Python backend crashed {} times. Please check the logs and restart manually.", MAX_RESTARTS);
                        println!("[tauri] {}", msg);
                        let _ = app_handle_for_restart.emit("python-error", msg);
                    }
                }
                _ => {}
            }
        }
    });

    Ok(())
}

/// 关闭 Python 后端
#[tauri::command]
fn shutdown_python(app_handle: tauri::AppHandle) -> Result<String, String> {
    println!("[tauri] Received command to shutdown Python backend.");
    cleanup_python_process(&app_handle);
    Ok("Python backend shutdown completed.".to_string())
}

/// 启动 Python 后端
#[tauri::command]
fn start_python(app_handle: tauri::AppHandle) -> Result<String, String> {
    println!("[tauri] Received command to start Python backend.");
    spawn_python_backend(app_handle)?;
    Ok("Python backend started.".to_string())
}

/// 获取 Python 配置
#[tauri::command]
fn get_python_config(app_handle: tauri::AppHandle) -> Result<PythonConfig, String> {
    if let Some(state) = app_handle.try_state::<Arc<Mutex<PythonProcess>>>() {
        let process_state = state.lock().map_err(|_| "Failed to acquire lock")?;
        Ok(process_state.config().clone())
    } else {
        Err("Python process state not found".to_string())
    }
}

// 保留旧的命令名称以保持兼容性
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
    // 加载配置
    let config = PythonConfig::load();
    
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .setup(move |app| {
            // 初始化 Python 进程状态
            app.manage(Arc::new(Mutex::new(PythonProcess::new(config.clone()))));
            
            // 设置窗口关闭事件处理
            let app_handle = app.handle().clone();
            if let Some(window) = app.get_webview_window("main") {
                window.on_window_event(move |event| {
                    match event {
                        tauri::WindowEvent::CloseRequested { .. } => {
                            println!("[tauri] Window close requested, cleaning up...");
                            cleanup_python_process(&app_handle);
                        }
                        tauri::WindowEvent::Destroyed => {
                            println!("[tauri] Window destroyed, cleaning up...");
                            cleanup_python_process(&app_handle);
                        }
                        _ => {}
                    }
                });
            }
            
            // 启动 Python 后端
            let app_handle = app.handle().clone();
            println!("[tauri] Starting Python backend...");
            spawn_python_backend(app_handle).ok();
            println!("[tauri] Python backend started.");
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            start_python,
            shutdown_python,
            start_sidecar,      // 兼容旧 API
            shutdown_sidecar,   // 兼容旧 API
            toggle_fullscreen,
            get_python_config
        ])
        .build(tauri::generate_context!())
        .expect("Error while running tauri application")
        .run(|app_handle, event| match event {
            RunEvent::ExitRequested { .. } => {
                println!("[tauri] Application exit requested, cleaning up...");
                cleanup_python_process(&app_handle);
            }
            RunEvent::Exit => {
                println!("[tauri] Application exiting, final cleanup...");
                cleanup_python_process(&app_handle);
            }
            _ => {}
        });
}
