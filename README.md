Panduan Instalasi XipserCloud Hosting Panel (Termux/VPS) v3
Panel ini dirancang untuk berjalan di lingkungan Linux (seperti Termux di Android atau VPS standar) dan memiliki fitur Firewall (iptables) nyata serta login yang dapat disesuaikan.
1. Persiapan Prasyarat Wajib
Pastikan Anda telah menginstal paket-paket berikut di Termux atau lingkungan Linux Anda. Paket iptables sangat penting untuk fitur firewall.
Perintah Instalasi Sekali Jalan:
Jalankan perintah ini di Terminal Anda:
pkg update && pkg upgrade -y
pkg install python git nginx mariadb php-fpm procps util-linux iptables -y

| Paket | Keterangan |
|---|---|
| python | Menjalankan backend server (server_app.py). |
| nginx | Server web (layanan yang dikontrol panel). |
| mariadb | Database (layanan yang dikontrol panel). |
| php-fpm | PHP FastCGI Process Manager (layanan yang dikontrol panel). |
| iptables | Wajib untuk kontrol Firewall nyata. |
| procps/util-linux | Digunakan untuk mendapatkan status sistem (uptime, top, dll.). |
2. Persiapan File Aplikasi
Pindahkan semua file yang baru saja Anda terima ke dalam satu folder proyek (misalnya, xipser_app).
A. Buat Folder Proyek dan Folder Situs:
mkdir xipser_app
cd xipser_app
# (Pindahkan semua file python, html, md, dan conf ke dalam folder ini)

B. Buat File Konfigurasi Wajib (config.json):
Anda harus membuat file ini untuk menentukan kredensial login Anda.
nano config.json

Isi file tersebut dengan format JSON berikut, ganti nilai username dan password sesuai keinginan Anda:
{
    "username": "admin-anda",
    "password": "sandi-rahasia-super-kuat"
}

Simpan dan keluar (Ctrl+X, lalu Y, lalu Enter jika menggunakan nano).
3. Menjalankan Panel Backend
Setelah config.json dibuat, Anda dapat memulai server Python.
A. Kunci Sesi Termux (Opsional tapi Direkomendasikan):
Untuk memastikan Termux tidak mematikan proses saat Anda beralih aplikasi:
termux-wake-lock

B. Jalankan Server:
python server_app.py

Server akan mencetak pesan status dan alamat akses di terminal, misalnya:
[*] Kredensial dimuat: User 'admin-anda'
======================================================================
  ⚡ XipserCloud PRODUCTION SERVER BERJALAN ⚡  
  Login: User 'admin-anda' | Password: (dari config.json)
======================================================================
  Akses Dashboard di Browser: http://[IP_ANDA]:8080
----------------------------------------------------------------------

4. Akses dan Login ke Panel
 * Buka browser di perangkat Anda (PC/Ponsel).
 * Akses alamat yang ditampilkan oleh server (contoh: http://192.168.1.5:8080).
 * Login menggunakan Username dan Password yang Anda setel di config.json.
Setelah login, Anda akan dapat:
 * Melihat Status VPS (CPU, RAM, Uptime).
 * Mengontrol layanan (Nginx, MariaDB, PHP-FPM) secara nyata.
 * Mengelola Database (CLI SQL).
 * Mengontrol Firewall menggunakan perintah iptables.
