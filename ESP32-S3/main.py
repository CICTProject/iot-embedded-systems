import machine
import socket
import network
import time
import gc
import os
import json
import neopixel

# ============================================================================
# SYSTEM INITIALIZATION
# ============================================================================
print("[INIT] BOOTING COMMAND CENTER KERNEL...")
gc.collect()

# Hardware Setup (NeoPixel on GPIO 48)
try:
    np = neopixel.NeoPixel(machine.Pin(48), 1)
    np[0] = (0, 50, 0) # Default: Matrix Green
    np.write()
except Exception as e:
    print(f"[WARN] LED INIT FAILED: {e}")

START_TIME = time.ticks_ms()
wlan = network.WLAN(network.STA_IF)

# ============================================================================
# FRONTEND PAYLOAD (HTML/CSS/JS)
# ============================================================================
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32-S3 // COMMAND CENTER</title>
    <style>
        :root { --bg: #050505; --fg: #00FF41; --dim: #003B00; --alert: #FF003C; --font: 'Courier New', Courier, monospace; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background-color: var(--bg); color: var(--fg); font-family: var(--font); overflow-x: hidden; }
        ::selection { background: var(--fg); color: var(--bg); }
        
        /* HEADER */
        header { border-bottom: 2px solid var(--fg); padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; background: #0a0a0a; text-shadow: 0 0 5px var(--fg); box-shadow: 0 4px 10px rgba(0, 255, 65, 0.1); }
        header h1 { font-size: 1.5rem; font-weight: bold; letter-spacing: 2px; }
        .blink { animation: blinker 1s linear infinite; }
        @keyframes blinker { 50% { opacity: 0; } }

        /* LAYOUT */
        .container { display: flex; height: calc(100vh - 60px); }
        .sidebar { width: 250px; border-right: 2px solid var(--dim); background: #080808; display: flex; flex-direction: column; }
        .nav-btn { background: none; border: none; border-bottom: 1px solid var(--dim); color: var(--fg); padding: 20px; text-align: left; font-family: var(--font); font-size: 1.1rem; cursor: pointer; transition: all 0.2s; text-transform: uppercase; letter-spacing: 1px; }
        .nav-btn:hover { background: var(--dim); padding-left: 25px; }
        .nav-btn.active { background: var(--fg); color: var(--bg); font-weight: bold; box-shadow: inset 5px 0 0 var(--bg); }
        
        .main-content { flex: 1; padding: 30px; overflow-y: auto; position: relative; }
        .main-content::before { content: " "; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,65,0.03) 2px, rgba(0,255,65,0.03) 4px); pointer-events: none; z-index: 999; }
        
        /* PANELS */
        .panel { display: none; animation: scanline 0.5s ease-out; }
        .panel.active { display: block; }
        @keyframes scanline { 0% { transform: translateY(-10px); opacity: 0; } 100% { transform: translateY(0); opacity: 1; } }
        
        h2 { border-bottom: 1px dashed var(--dim); padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
        
        /* CARDS & COMPONENTS */
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { border: 1px solid var(--dim); padding: 20px; background: rgba(0, 59, 0, 0.1); position: relative; }
        .card::before { content: ''; position: absolute; top: -1px; left: -1px; width: 10px; height: 10px; border-top: 2px solid var(--fg); border-left: 2px solid var(--fg); }
        .card::after { content: ''; position: absolute; bottom: -1px; right: -1px; width: 10px; height: 10px; border-bottom: 2px solid var(--fg); border-right: 2px solid var(--fg); }
        
        .stat-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #111; }
        .stat-val { font-weight: bold; text-shadow: 0 0 8px var(--fg); }
        
        /* TERMINAL */
        .term-box { background: #000; border: 1px solid var(--dim); padding: 15px; height: 400px; overflow-y: auto; font-size: 0.9rem; line-height: 1.5; }
        .term-line::before { content: "root@esp32:~# "; color: #888; }
        .term-input { width: 100%; background: transparent; border: none; color: var(--fg); font-family: var(--font); font-size: 0.9rem; outline: none; margin-top: 10px; }
        
        /* CONTROLS */
        .rgb-controls { display: flex; gap: 10px; margin-top: 15px; }
        input[type="number"] { background: transparent; border: 1px solid var(--fg); color: var(--fg); padding: 8px; font-family: var(--font); width: 80px; text-align: center; }
        button.action-btn { background: transparent; border: 1px solid var(--fg); color: var(--fg); padding: 8px 20px; font-family: var(--font); cursor: pointer; text-transform: uppercase; font-weight: bold; transition: all 0.2s; }
        button.action-btn:hover, button.action-btn:active { background: var(--fg); color: var(--bg); box-shadow: 0 0 15px var(--fg); }
        
        .fs-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .fs-table th, .fs-table td { text-align: left; padding: 10px; border-bottom: 1px dashed var(--dim); }
        .fs-table th { color: #888; }
    </style>
</head>
<body>

<header>
    <h1>[ ESP32-S3 // COMMAND_CENTER ]</h1>
    <div>STATUS: <span class="blink">ONLINE</span> | IP: <span id="ip-display">RESOLVING...</span></div>
</header>

<div class="container">
    <div class="sidebar">
        <button class="nav-btn active" onclick="switchTab('sys')">01. Diagnostics</button>
        <button class="nav-btn" onclick="switchTab('hw')">02. Hardware_OVR</button>
        <button class="nav-btn" onclick="switchTab('fs')">03. Storage_Node</button>
        <button class="nav-btn" onclick="switchTab('term')">04. Secure_Shell</button>
    </div>

    <div class="main-content">
        <div id="tab-sys" class="panel active">
            <h2>System Diagnostics</h2>
            <div class="grid">
                <div class="card">
                    <h3>[ MEMORY_ALLOCATION ]</h3>
                    <div class="stat-row"><span>Total RAM:</span><span class="stat-val">~320 KB</span></div>
                    <div class="stat-row"><span>Free RAM:</span><span class="stat-val" id="sys-mem">CALCULATING...</span></div>
                    <div class="stat-row"><span>Garbage Collect:</span><span class="stat-val" id="sys-gc">IDLE</span></div>
                </div>
                <div class="card">
                    <h3>[ CORE_METRICS ]</h3>
                    <div class="stat-row"><span>CPU Freq:</span><span class="stat-val" id="sys-cpu">...</span></div>
                    <div class="stat-row"><span>Uptime:</span><span class="stat-val" id="sys-up">...</span></div>
                    <div class="stat-row"><span>Platform:</span><span class="stat-val">MicroPython</span></div>
                </div>
            </div>
        </div>

        <div id="tab-hw" class="panel">
            <h2>Hardware Override</h2>
            <div class="card" style="max-width: 500px;">
                <h3>[ NEOPIXEL_ARRAY_CTRL ]</h3>
                <p style="margin-top: 10px; color: #888;">Inject direct RGB values to GPIO 48 vector.</p>
                <div class="rgb-controls">
                    <input type="number" id="val-r" min="0" max="255" placeholder="R">
                    <input type="number" id="val-g" min="0" max="255" placeholder="G">
                    <input type="number" id="val-b" min="0" max="255" placeholder="B">
                    <button class="action-btn" onclick="transmitRGB()">TRANSMIT</button>
                </div>
                <div id="hw-status" style="margin-top: 15px; font-size: 0.9em; color: var(--alert);"></div>
            </div>
        </div>

        <div id="tab-fs" class="panel">
            <h2>Storage Node Access</h2>
            <div class="card">
                <h3>[ ROOT_DIRECTORY ]</h3>
                <button class="action-btn" style="margin-top: 10px;" onclick="fetchFS()">SCAN DIRECTORY</button>
                <table class="fs-table">
                    <thead><tr><th>FILENAME</th><th>TYPE</th></tr></thead>
                    <tbody id="fs-list">
                        <tr><td colspan="2" style="color:#888;">Awaiting scan command...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div id="tab-term" class="panel">
            <h2>Secure Shell Emulator</h2>
            <div class="term-box" id="term-box">
                <div style="color: #888; margin-bottom: 10px;">ESP32-S3 KERNEL LOGS. UNAUTHORIZED ACCESS PROHIBITED.</div>
            </div>
            <div style="display: flex;">
                <span style="color: #888; margin-top: 12px; margin-right: 5px;">root@esp32:~#</span>
                <input type="text" class="term-input" id="term-cmd" placeholder="Enter command..." onkeypress="handleTerm(event)">
            </div>
        </div>
    </div>
</div>

<script>
    // TAB SWITCHING LOGIC
    function switchTab(tabId) {
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.getElementById('tab-' + tabId).classList.add('active');
        event.target.classList.add('active');
        logTerm(`Switching context to NODE_${tabId.toUpperCase()}`);
    }

    // TERMINAL LOGIC
    const termBox = document.getElementById('term-box');
    function logTerm(msg) {
        const div = document.createElement('div');
        div.className = 'term-line';
        div.textContent = msg;
        termBox.appendChild(div);
        termBox.scrollTop = termBox.scrollHeight;
    }
    
    function handleTerm(e) {
        if(e.key === 'Enter') {
            const cmd = e.target.value;
            logTerm(cmd);
            e.target.value = '';
            if(cmd === 'clear') termBox.innerHTML = '';
            else setTimeout(() => logTerm(`bash: ${cmd}: command not found`), 200);
        }
    }

    // API DATA POLLING (SYSTEM DIAGNOSTICS)
    setInterval(async () => {
        if(document.getElementById('tab-sys').classList.contains('active')) {
            try {
                const res = await fetch('/api/sys');
                const data = await res.json();
                document.getElementById('sys-mem').textContent = data.mem_free + ' Bytes';
                document.getElementById('sys-gc').textContent = data.mem_alloc + ' Bytes Alloc';
                document.getElementById('sys-cpu').textContent = (data.cpu_freq / 1000000) + ' MHz';
                
                let up_s = Math.floor(data.uptime / 1000);
                let m = Math.floor(up_s / 60);
                let s = up_s % 60;
                document.getElementById('sys-up').textContent = `${m}m ${s}s`;
                document.getElementById('ip-display').textContent = data.ip;
            } catch(e) {}
        }
    }, 2000);

    // API HARDWARE OVERRIDE
    async function transmitRGB() {
        const r = document.getElementById('val-r').value || 0;
        const g = document.getElementById('val-g').value || 0;
        const b = document.getElementById('val-b').value || 0;
        const status = document.getElementById('hw-status');
        
        status.textContent = `TRANSMITTING PKT: [${r}, ${g}, ${b}]...`;
        logTerm(`TRANSMIT_RGB: R${r} G${g} B${b}`);
        
        try {
            const res = await fetch(`/api/led?r=${r}&g=${g}&b=${b}`);
            if(res.ok) {
                status.style.color = "var(--fg)";
                status.textContent = "PAYLOAD DELIVERED SUCCESSFULLY.";
            }
        } catch(e) {
            status.style.color = "var(--alert)";
            status.textContent = "TRANSMISSION FAILED: ERR_NETWORK.";
        }
    }

    // API FILE SYSTEM SCAN
    async function fetchFS() {
        logTerm('INITIATING STORAGE_NODE SCAN...');
        const tbody = document.getElementById('fs-list');
        tbody.innerHTML = '<tr><td colspan="2">Scanning sectors...</td></tr>';
        
        try {
            const res = await fetch('/api/fs');
            const data = await res.json();
            tbody.innerHTML = '';
            data.files.forEach(f => {
                const ext = f.split('.').pop();
                const type = ext === 'py' ? 'SYSTEM_SCRIPT' : (ext === 'json' ? 'DATA_BLOB' : 'UNKNOWN_OBJ');
                tbody.innerHTML += `<tr><td>${f}</td><td style="color:var(--dim)">[ ${type} ]</td></tr>`;
            });
            logTerm('STORAGE SCAN COMPLETE.');
        } catch(e) {
            tbody.innerHTML = '<tr><td colspan="2" style="color:var(--alert)">ACCESS DENIED OR IO_ERROR</td></tr>';
        }
    }
    
    // Initial Boot Log
    setTimeout(() => logTerm('INITIALIZATION SEQUENCE COMPLETE.'), 500);
</script>
</body>
</html>
"""

# ============================================================================
# REST API HANDLERS
# ============================================================================
def get_sys_info():
    gc.collect()
    return json.dumps({
        "mem_free": gc.mem_free(),
        "mem_alloc": gc.mem_alloc(),
        "cpu_freq": machine.freq(),
        "uptime": time.ticks_diff(time.ticks_ms(), START_TIME),
        "ip": wlan.ifconfig()[0] if wlan.isconnected() else "DISCONNECTED"
    })

def get_fs_info():
    files = os.listdir()
    return json.dumps({"files": files})

# ============================================================================
# MAIN ASYNC-LIKE SERVER LOOP
# ============================================================================
def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
    
    # Non-blocking timeout allows the While loop to breathe and GC to run
    s.settimeout(0.2) 
    
    print(f"[SYS] COMMAND CENTER LISTENING ON HTTP://{wlan.ifconfig()[0]}")
    
    while True:
        try:
            conn, addr = s.accept()
            conn.settimeout(1.0)
            request = conn.recv(1024).decode()
            
            # --- ROUTER LOGIC ---
            if "GET /api/sys" in request:
                response = get_sys_info()
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response.encode())
                
            elif "GET /api/fs" in request:
                response = get_fs_info()
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + response.encode())
                
            elif "GET /api/led" in request:
                # Parse: /api/led?r=255&g=0&b=100
                try:
                    params = request.split('GET /api/led?')[1].split(' ')[0]
                    pairs = params.split('&')
                    r, g, b = 0, 0, 0
                    for p in pairs:
                        if '=' not in p: continue
                        k, v = p.split('=')
                        if k == 'r': r = int(v)
                        if k == 'g': g = int(v)
                        if k == 'b': b = int(v)
                    np[0] = (r, g, b)
                    np.write()
                    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"ok\"}")
                except Exception:
                    conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                    
            elif "GET / " in request or "GET /?" in request:
                # Gửi cục HTML Payload khổng lồ
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n")
                # Chunking để tránh đầy RAM khi send
                chunk_size = 1024
                for i in range(0, len(DASHBOARD_HTML), chunk_size):
                    conn.sendall(DASHBOARD_HTML[i:i+chunk_size].encode())
            else:
                conn.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
                
            conn.close()
            
        except OSError:
            # Timeout do không có ai truy cập, đi qua vòng lặp tiếp
            pass
        except Exception as e:
            print(f"[ERR] SERVER FAULT: {e}")
            try:
                conn.close()
            except:
                pass
                
        # Duy trì sự sống cho hệ thống
        time.sleep(0.01)

# Execute
start_server()