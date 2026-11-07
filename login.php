<?php
require_once __DIR__ . '/auth.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$raw = file_get_contents('php://input');
$payload = json_decode($raw, true) ?: $_POST;

$email = trim((string)($payload['email'] ?? ''));
$password = (string)($payload['password'] ?? '');

$conn = get_db();
$stmt = $conn->prepare("SELECT id, password_hash FROM users WHERE email = ?");
$stmt->bind_param('s', $email);
$stmt->execute();
$user = $stmt->get_result()->fetch_assoc();

if (!$user || !password_verify($password, $user['password_hash'])) {
    http_response_code(401);
    echo json_encode(['error' => 'invalid_credentials']);
    exit;
}

$update = $conn->prepare("UPDATE users SET login_count = login_count + 1, last_login_at = NOW() WHERE id = ?");
$update->bind_param('i', $user['id']);
$update->execute();

$session = create_session($conn, (int)$user['id']);
echo json_encode(['ok' => true, 'token' => $session['token'], 'expires_at' => $session['expires_at']]);
