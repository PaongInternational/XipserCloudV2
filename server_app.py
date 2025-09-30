# -*- coding: utf-8 -*-
# XIPSERCLOUD SERVER APP - Menghandle eksekusi perintah Termux nyata (v3)
# Kredensial Login dimuat dari: config.json

import http.server
import socketserver
import json
import os
import socket
import subprocess
import time

PORT = 8080
DASHBOARD_FILE = 'dashboard_app.html'
CONFIG_FILE = 'config.json'
DASHBOARD_CONTENT = ""
SITE_ROOT = "./sites/" 

# Variabel Global
USERS = {} # Akan dimuat dari config.json

# --- Fungsi Utility Dasar ---
def load_config():
    """Memuat konten konfigurasi dari config.json."""
    global USERS
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # USERS hanya menampung satu pasangan user/pass dari file konfigurasi
            USERS[config.get("username", "admin")] = config.get("password", "12345")
            print(f"[*] Kredensial dimuat: User '{list(USERS.keys())[0]}'")
    except FileNotFoundError:
        print(f"[ERROR KRITIS] File '{CONFIG_FILE}' tidak ditemukan!")
        print("Pastikan Anda membuat file config.json dengan username dan password.")
        exit(1)
    except Exception as e:
        print(f"[ERROR] Gagal memuat konfigurasi: {e}")
        exit(1)

def load_dashboard_content():
    """Memuat konten HTML dashboard."""
    global DASHBOARD_CONTENT
    try:
        with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
            DASHBOARD_CONTENT = f.read()
    except Exception as e:
        print(f"[ERROR] Gagal memuat dashboard HTML: {e}")
        exit(1)

def execute_command(command, background=False):
    """Menjalankan perintah shell di Termux."""
    print(f"[*] Menjalankan perintah: {command}")
    
    if background:
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1) 
        return "RUNNING_BG", f"Perintah latar belakang dikirim. PID: {p.pid}"

    try:
        # Menghilangkan pesan Termux 'Setting up...' yang bisa mengacaukan JSON
        command_cleaned = f"env -i PATH=$PATH {command}" 
        result = subprocess.run(command_cleaned, shell=True, capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        status = "SUCCESS" if result.returncode == 0 and "No such file or directory" not in output else "ERROR"
        return status, output
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "Perintah melebihi batas waktu (15 detik)."
    except Exception as e:
        return "CRITICAL_ERROR", str(e)

# (get_local_ip, get_system_status, handle_service_command, handle_site_creation, handle_db_command 
# tetap sama, hanya menggunakan fungsi execute_command yang sudah ditingkatkan)

def get_system_status():
    """Mendapatkan data status sistem REAL-TIME (CPU, RAM, Uptime)."""
    status = {}
    
    # Perintah Termux untuk Status
    uptime_cmd = "uptime -p"
    top_cmd = "top -n 1 -b" 
    meminfo_cmd = "cat /proc/meminfo"
    
    # 1. Uptime
    status["uptime"] = execute_command(uptime_cmd)[1].strip() or "N/A"
    
    # 2. CPU/Load Average
    top_output = execute_command(top_cmd)[1]
    load_avg_line = [line for line in top_output.split('\n') if 'load average' in line]
    status["load_avg_1m"] = float(load_avg_line[0].split('load average:')[1].strip().split(',')[0]) if load_avg_line else 0.0
    
    cpu_line = [line for line in top_output.split('\n') if '%Cpu' in line]
    if cpu_line:
        idle_str = [part for part in cpu_line[0].split(',') if 'id' in part][0]
        idle_perc = float(idle_str.strip().split()[0])
        status["cpu_usage"] = round(100.0 - idle_perc, 1)
    else:
         status["cpu_usage"] = 0.0

    # 3. RAM Usage
    meminfo = execute_command(meminfo_cmd)[1]
    mem_total_kb, mem_available_kb = 0, 0
    for line in meminfo.split('\n'):
        if "MemTotal:" in line: mem_total_kb = int(line.split()[1])
        if "MemAvailable:" in line: mem_available_kb = int(line.split()[1])
    
    status["ram_total_gb"] = round(mem_total_kb / (1024*1024), 2)
    status["ram_used_gb"] = round((mem_total_kb - mem_available_kb) / (1024*1024), 2)

    status["timestamp"] = time.time()
    return status

def handle_service_command(data):
    """Menangani permintaan Start, Stop, Restart, Status layanan nyata."""
    # (Logika Service Command tetap sama)
    command_type = data.get('type')
    service = data.get('service')
    
    pid_check_cmd = {
        'Nginx': "pgrep -f 'nginx' -a",
        'MariaDB': "pgrep -f 'mysqld' -a",
        'PHP-FPM': "pgrep -f 'php-fpm' -a",
    }
    
    service_cmd = {
        'Nginx': {'start': "nginx", 'stop': "pkill -f 'nginx'"},
        'MariaDB': {'start': "mysqld_safe &", 'stop': "pkill -f 'mysqld'"}, 
        'PHP-FPM': {'start': "php-fpm", 'stop': "pkill -f 'php-fpm'"}, 
    }

    if service not in service_cmd:
        return {"status": "ERROR", "message": f"Layanan '{service}' tidak dikenal."}

    if command_type == 'status':
        status, output = execute_command(pid_check_cmd[service])
        is_running = any(line.strip() and not line.strip().startswith('pgrep') for line in output.split('\n'))
        
        if is_running:
            return {"status": "RUNNING", "message": f"{service} sedang berjalan.", "log": output}
        else:
            return {"status": "STOPPED", "message": f"{service} tidak berjalan.", "log": "Proses tidak ditemukan."}

    elif command_type == 'start':
        status_result = handle_service_command({'type': 'status', 'service': service})
        if status_result['status'] == 'RUNNING':
             return {"status": "ALREADY_RUNNING", "message": f"{service} sudah berjalan.", "log": status_result['log']}
             
        is_background = (service == 'MariaDB' or service == 'PHP-FPM') 
        status, output = execute_command(service_cmd[service]['start'], background=is_background)
        
        time.sleep(2) 
        final_status = handle_service_command({'type': 'status', 'service': service})
        
        if final_status['status'] == 'RUNNING':
            return {"status": "SUCCESS", "message": f"{service} berhasil di-START.", "log": final_status['log']}
        else:
            return {"status": "FAIL", "message": f"Gagal START {service}. Cek log Termux.", "log": output + "\n" + final_status['log']}

    elif command_type == 'stop':
        status, output = execute_command(service_cmd[service]['stop'])
        time.sleep(1) 
        final_status = handle_service_command({'type': 'status', 'service': service})

        if final_status['status'] == 'STOPPED':
            return {"status": "SUCCESS", "message": f"{service} berhasil di-STOP.", "log": output}
        else:
             return {"status": "FAIL", "message": f"Gagal STOP {service}.", "log": output}
        
    elif command_type == 'restart':
        stop_result = handle_service_command({'type': 'stop', 'service': service})
        start_result = handle_service_command({'type': 'start', 'service': service})
        
        return {
            "status": "SUCCESS" if start_result['status'] == 'SUCCESS' else "FAIL", 
            "message": f"{service} di-RESTART. Status Start: {start_result['status']}.",
            "log": f"--- STOP LOG ---\n{stop_result['log']}\n--- START LOG ---\n{start_result['log']}"
        }
        
    return {"status": "ERROR", "message": "Perintah tidak valid."}
    
def handle_db_command(data):
    """Menangani eksekusi perintah SQL nyata."""
    sql_query = data.get('query')
    command = f"mysql -e \"{sql_query}\""
    
    if not sql_query:
        return {"status": "ERROR", "message": "Query SQL tidak boleh kosong."}

    status, output = execute_command(command)
    
    if status == 'SUCCESS' or "Warning:" in output:
        return {"status": "SUCCESS", "message": "Query berhasil dieksekusi.", "log": output}
    else:
        return {"status": "FAIL", "message": "Query gagal. Cek log MariaDB/error syntax.", "log": output}

def handle_site_creation(data):
    """Menangani pembuatan struktur folder situs baru (Deployment Mock)."""
    # (Logika Site Creation tetap sama)
    domain = data.get('domain')
    php_version = data.get('php_version', 'php8')
    
    if not domain:
        return {"status": "ERROR", "message": "Nama domain wajib diisi."}
    
    site_path = os.path.join(SITE_ROOT, domain)
    public_html_path = os.path.join(site_path, 'public_html')

    try:
        if os.path.exists(site_path):
            return {"status": "ERROR", "message": f"Direktori situs '{domain}' sudah ada."}
        
        os.makedirs(public_html_path)
        
        index_content = f"""
        <html>
        <head><title>Situs {domain} Aktif</title></head>
        <body>
            <h1>Situs XipserCloud Berhasil Dideploy!</h1>
            <p>Ini adalah halaman default untuk domain {domain}.</p>
            <p>PHP Version Terpilih: {php_version}</p>
        </body>
        </html>
        """
        with open(os.path.join(public_html_path, 'index.html'), 'w') as f:
            f.write(index_content)
        
        nginx_config_note = f"""
        --- PERHATIAN NGINX ---
        Untuk mengaktifkan situs ini, Anda perlu membuat file konfigurasi Nginx 
        di direktori sites-enabled Termux Anda, menunjuk ke: {os.getcwd()}/{public_html_path}
        Gunakan template 'nginx_site_template.conf' yang disediakan.
        """

        return {
            "status": "SUCCESS", 
            "message": f"Situs {domain} berhasil dibuat! Folder: {site_path}", 
            "log": nginx_config_note
        }
        
    except Exception as e:
        return {"status": "CRITICAL_ERROR", "message": f"Gagal membuat situs: {str(e)}", "log": str(e)}

# --- Fungsionalitas Firewall (iptables NYATA) ---
def handle_firewall_command(data):
    """Menangani eksekusi perintah iptables."""
    action = data.get('action')
    
    # 1. LIST RULES
    if action == 'list':
        command = "iptables -nL INPUT --line-numbers"
        status, output = execute_command(command)
        
        # Format output menjadi list of strings per line
        rules = [line.strip() for line in output.split('\n') if line.strip() and not line.startswith('Chain')]
        
        if status == 'SUCCESS':
            # Baris pertama biasanya header, ambil sisanya
            return {"status": "SUCCESS", "message": "Aturan Firewall berhasil dimuat.", "rules": rules}
        else:
            return {"status": "FAIL", "message": "Gagal memuat aturan. Pastikan iptables terinstal!", "log": output, "rules": []}

    # 2. ADD RULE
    elif action == 'add':
        chain = data.get('chain', 'INPUT')
        protocol = data.get('protocol', 'tcp')
        target = data.get('target', 'ACCEPT') # ACCEPT/DROP
        port = data.get('port')
        source_ip = data.get('source_ip', '') # Optional

        if not port:
            return {"status": "ERROR", "message": "Port wajib diisi untuk penambahan aturan."}

        # Contoh command: iptables -A INPUT -p tcp --dport 80 -j ACCEPT
        command = f"iptables -A {chain} -p {protocol} --dport {port} -j {target}"
        if source_ip:
             command = f"iptables -A {chain} -s {source_ip} -j {target}"
             
        status, output = execute_command(command)
        
        if status == 'SUCCESS':
            return {"status": "SUCCESS", "message": f"Aturan {target} Port {port} berhasil ditambahkan.", "log": output}
        else:
            return {"status": "FAIL", "message": f"Gagal menambahkan aturan. Error: {output}", "log": output}
            
    # 3. DELETE RULE
    elif action == 'delete':
        line_number = data.get('line_number')
        chain = data.get('chain', 'INPUT')

        if not line_number or not str(line_number).isdigit():
            return {"status": "ERROR", "message": "Nomor baris (Line Number) wajib diisi dan harus berupa angka."}

        # Contoh command: iptables -D INPUT 5
        command = f"iptables -D {chain} {line_number}"
        
        status, output = execute_command(command)
        
        if status == 'SUCCESS':
            return {"status": "SUCCESS", "message": f"Aturan baris ke-{line_number} berhasil dihapus.", "log": output}
        else:
            return {"status": "FAIL", "message": f"Gagal menghapus aturan. Error: {output}", "log": output}

    # 4. RESET (Flush All Rules)
    elif action == 'flush':
        command = "iptables -F"
        status, output = execute_command(command)
        
        if status == 'SUCCESS':
            return {"status": "SUCCESS", "message": "Semua aturan Firewall berhasil di-FLUSH (dihapus).", "log": output}
        else:
            return {"status": "FAIL", "message": f"Gagal FLUSH aturan. Error: {output}", "log": output}

    return {"status": "ERROR", "message": "Perintah Firewall tidak valid."}


# --- Handler Permintaan HTTP ---
class XipserHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/' or self.path == '/dashboard_app.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(DASHBOARD_CONTENT.encode('utf-8'))
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = json.dumps(get_system_status())
            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_error(404, "File/Endpoint Tidak Ditemukan")

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # Autentikasi dilakukan untuk setiap POST request
        username = data.get('username')
        password = data.get('password')
        
        if self.path == '/login':
            if USERS.get(username) == password:
                response = json.dumps({"success": True, "message": "Login berhasil!", "user": username})
            else:
                self.send_response(401)
                response = json.dumps({"success": False, "message": "Username atau Password salah."})
        
        elif USERS.get(username) == password:
            if self.path == '/api/service_command':
                result = handle_service_command(data)
                response = json.dumps(result)
                
            elif self.path == '/api/site_management':
                result = handle_site_creation(data)
                response = json.dumps(result)

            elif self.path == '/api/db_execute':
                result = handle_db_command(data)
                response = json.dumps(result)

            elif self.path == '/api/firewall_command':
                result = handle_firewall_command(data)
                response = json.dumps(result)
            
            else:
                self.send_response(404)
                response = json.dumps({"status": "ERROR", "message": "Endpoint Tidak Ditemukan"})
        else:
             self.send_response(401)
             response = json.dumps({"success": False, "message": "Sesi berakhir. Silakan login kembali."})
            
        self.wfile.write(response.encode('utf-8'))


# --- Main Program ---
if __name__ == '__main__':
    load_config() # MEMUAT KONFIGURASI BARU
    os.makedirs(SITE_ROOT, exist_ok=True)
    load_dashboard_content()
    
    IP_ADDRESS = socket.gethostbyname(socket.gethostname())
    
    try:
        with socketserver.TCPServer(('0.0.0.0', PORT), XipserHandler) as httpd:
            print("="*70)
            print(f"  ⚡ XipserCloud PRODUCTION SERVER BERJALAN ⚡  ")
            print(f"  Login: User '{list(USERS.keys())[0]}' | Password: (dari config.json)")
            print("="*70)
            print(f"  Akses Dashboard di Browser: http://{IP_ADDRESS}:{PORT}")
            print("-" * 70)
            httpd.serve_forever()
    except OSError as e:
        print(f"\n[KRITIS] Gagal memulai server (Port {PORT} mungkin sudah digunakan): {e}")
    except KeyboardInterrupt:
        print("\n[INFO] Server dihentikan oleh pengguna.")
