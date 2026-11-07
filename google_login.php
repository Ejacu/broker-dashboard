<?php
require_once __DIR__ . '/auth.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$raw = file_get_contents('php://input');
$payload = json_decode($raw, true) ?: $_POST;
$credential = (string)($payload['credential'] ?? '');

if ($credential === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing_credential']);
    exit;
}

// 用 Google 的 tokeninfo 端點驗證這個憑證真的是 Google 簽發、沒過期、而且是發給我們這個 Client ID 的,
// 不用自己處理 JWT 簽章驗證,簡單可靠,流量不大的話完全夠用
$verifyUrl = 'https://oauth2.googleapis.com/tokeninfo?id_token=' . urlencode($credential);
$ctx = stream_context_create(['http' => ['timeout' => 10]]);
$resp = @file_get_contents($verifyUrl, false, $ctx);

if ($resp === false) {
    http_response_code(502);
    echo json_encode(['error' => 'google_verify_failed']);
    exit;
}

$info = json_decode($resp, true);
if (
    !$info
    || ($info['aud'] ?? '') !== GOOGLE_CLIENT_ID
    || empty($info['email'])
    || ($info['email_verified'] ?? 'false') !== 'true'
) {
    http_response_code(401);
    echo json_encode(['error' => 'invalid_google_token']);
    exit;
}

$email = $info['email'];
$conn = get_db();

$stmt = $conn->prepare("SELECT id FROM users WHERE email = ?");
$stmt->bind_param('s', $email);
$stmt->execute();
$user = $stmt->get_result()->fetch_assoc();

if ($user) {
    $user_id = (int)$user['id'];
} else {
    $ip = $_SERVER['REMOTE_ADDR'] ?? null;
    $referrer = $_SERVER['HTTP_REFERER'] ?? null;
    $ins = $conn->prepare("INSERT INTO users (email, password_hash, auth_provider, signup_ip, signup_referrer) VALUES (?, NULL, 'google', ?, ?)");
    $ins->bind_param('sss', $email, $ip, $referrer);
    $ins->execute();
    $user_id = $conn->insert_id;
}

$update = $conn->prepare("UPDATE users SET login_count = login_count + 1, last_login_at = NOW() WHERE id = ?");
$update->bind_param('i', $user_id);
$update->execute();

$session = create_session($conn, $user_id);
echo json_encode(['ok' => true, 'token' => $session['token'], 'expires_at' => $session['expires_at']]);
