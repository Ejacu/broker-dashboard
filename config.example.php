<?php
// 複製這個檔案為 config.php,只上傳 config.php 到 Bluehost 主機,
// 並填入 cPanel -> MySQL 資料庫 頁面看到的實際值。
// config.php 已經被 .gitignore 排除,絕對不要把它 commit 進 git。

define('DB_HOST', 'localhost');           // Bluehost 幾乎都是 localhost
define('DB_NAME', 'your_cpanel_dbname');  // cPanel 建立的資料庫全名,通常是 帳號前綴_資料庫名
define('DB_USER', 'your_cpanel_dbuser');  // cPanel 建立的資料庫使用者,通常是 帳號前綴_使用者名
define('DB_PASS', 'your_cpanel_dbpass');

// 上傳資料用的密鑰,自己隨便打一長串英數字亂碼即可,
// 要跟 GitHub Actions 的 UPLOAD_TOKEN secret 設成完全一樣的值
define('UPLOAD_TOKEN', 'CHANGE_ME_TO_A_LONG_RANDOM_STRING');

// 前端(Vercel)網域,只允許這個來源讀取資料
define('ALLOWED_ORIGIN', 'https://broker.tarotstock.com');

function send_cors_headers() {
    header('Access-Control-Allow-Origin: ' . ALLOWED_ORIGIN);
    header('Access-Control-Allow-Methods: GET, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        http_response_code(204);
        exit;
    }
}

function get_db() {
    $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    if ($conn->connect_error) {
        http_response_code(500);
        die(json_encode(['error' => 'db_connect_failed']));
    }
    $conn->set_charset('utf8mb4');
    return $conn;
}
