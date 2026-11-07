<?php
// 共用登入驗證邏輯,所有需要登入才能用的 API 都引用這支(取代直接引用 config.php)
require_once __DIR__ . '/config.php';

const SESSION_DAYS = 30;   // 滑動展延天數:只要期限內有再使用,就自動往後推
const FREE_STOCK_ID = '2330'; // 免費試看股票,不用登入也能查這一檔的完整資料

// 去 Google Cloud Console 申請的 OAuth 用戶端 ID,這個是公開識別碼不是密碼,可以放心寫在這裡
const GOOGLE_CLIENT_ID = '105409233217-i3or2ffhst67bbhis9le86qm0ldp7ovo.apps.googleusercontent.com';

function generate_token(): string {
    return bin2hex(random_bytes(32));
}

function create_session(mysqli $conn, int $user_id): array {
    $token = generate_token();
    $expires = date('Y-m-d H:i:s', time() + SESSION_DAYS * 86400);
    $stmt = $conn->prepare("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)");
    $stmt->bind_param('sis', $token, $user_id, $expires);
    $stmt->execute();
    return ['token' => $token, 'expires_at' => $expires];
}

// 驗證目前請求帶的 token,有效回傳 user_id,無效/沒帶回傳 null(不會自己結束程式)
function validate_token(mysqli $conn): ?int {
    $token = $_GET['auth_token'] ?? $_POST['auth_token'] ?? '';
    if ($token === '') {
        return null;
    }

    $stmt = $conn->prepare("SELECT user_id, expires_at FROM sessions WHERE token = ?");
    $stmt->bind_param('s', $token);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();

    if (!$row || strtotime($row['expires_at']) < time()) {
        return null;
    }

    // 滑動展延:只要還在用,有效期就往後推 SESSION_DAYS 天
    $newExpires = date('Y-m-d H:i:s', time() + SESSION_DAYS * 86400);
    $upd = $conn->prepare("UPDATE sessions SET expires_at = ? WHERE token = ?");
    $upd->bind_param('ss', $newExpires, $token);
    $upd->execute();

    // 真人每次用有效 session 查資料就會經過這裡,順便記最近活躍時間——
    // 比 login_count(只在重新輸入帳密/重新 Google 登入時才會動,30 天 session 期間內通常不會再觸發)更能反映真實使用狀況
    $touch = $conn->prepare("UPDATE users SET last_active_at = NOW() WHERE id = ?");
    $touch->bind_param('i', $row['user_id']);
    $touch->execute();

    return (int)$row['user_id'];
}

// 給 GitHub Actions / 本機背景腳本用的後門:帶上跟 upload.php 一樣的 UPLOAD_TOKEN
// 就能跳過真人登入驗證,因為這些程式是自動化腳本,沒辦法走一般的登入流程
function is_valid_service_token(): bool {
    $token = $_GET['service_token'] ?? $_POST['service_token'] ?? '';
    return $token !== '' && hash_equals(UPLOAD_TOKEN, $token);
}

// 驗證 token,成功回傳 user_id;失敗直接回 401 並結束整支 API
function require_auth(mysqli $conn): int {
    if (is_valid_service_token()) {
        return 0; // 0 代表自動化腳本,不是真人會員
    }
    $user_id = validate_token($conn);
    if ($user_id === null) {
        http_response_code(401);
        echo json_encode(['error' => 'unauthorized']);
        exit;
    }
    return $user_id;
}

// 跟 require_auth 一樣,但如果查詢的是免費試看股票,沒登入也放行(回傳 null 代表匿名訪客)
function require_auth_or_free_stock(mysqli $conn, string $stock_id): ?int {
    if (is_valid_service_token()) {
        return 0;
    }
    $user_id = validate_token($conn);
    if ($user_id !== null) {
        return $user_id;
    }
    if ($stock_id === FREE_STOCK_ID) {
        return null;
    }
    http_response_code(401);
    echo json_encode(['error' => 'unauthorized']);
    exit;
}
