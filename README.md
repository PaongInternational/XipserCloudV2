Panduan Instalasi XipserCloud Hosting Panel (Termux/VPS)
Panel ini adalah prototipe fungsional yang memungkinkan Anda mengontrol layanan Nginx, MariaDB, PHP-FPM, dan Database CLI nyata melalui antarmuka web yang berjalan di Termux.
Prasyarat Wajib (Instalasi Termux)
Pastikan Anda telah menginstal paket-paket berikut di Termux:
 * Server Web: nginx
 * Database: mariadb (atau mysql)
 * PHP Processor: php-fpm
 * Backend & Tools: python, git, procps, util-linux (untuk data status CPU/RAM)
Perintah Instalasi Sekali Jalan:
pkg update && pkg upgrade -y
pkg install python git nginx mariadb php-fpm procps util-linux -y

Langkah Instalasi
Langkah 1: Kloning & Persiapan Direktori
Pindahkan kedua file (server_app.py dan dashboard_app.html) ke satu folder.
# Ganti 'xipser_app' dengan nama folder proyek Anda
mkdir xipser_app
cd xipser_app

# Di sini, pastikan Anda menempatkan server_app.py dan dashboard_app.html
# Juga simpan nginx_site_template.conf di sini sebagai referensi.

Langkah 2: Menjalankan Panel Backend
Jalankan server Python di Termux. Ini akan menjadi API yang mengontrol sistem Anda.
# Kunci sesi Termux agar tidak mati saat server berjalan
termux-wake-lock

# Jalankan server
python server_app.py

