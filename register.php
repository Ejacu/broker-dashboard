<?php
require_once __DIR__ . '/auth.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$raw = file_get_contents('php://input');
$payload = json_decode($raw, true) ?: $_POST;

$email = trim((string)($payload['email'] ?? ''));
$password = (string)($payload['password'] ?? '');

if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo json_encode(['error' => 'invalid_email']);
    exit;
}
if (strlen($password) < 6) {
    http_response_code(400);
    echo json_encode(['error' => 'password_too_short']);
    exit;
}

$conn = get_db();

$check = $conn->prepare("SELECT id FROM users WHERE email = ?");
$check->bind_param('s', $email);
$check->execute();
if ($check->get_result()->fetch_assoc()) {
    http_response_code(409);
    echo json_encode(['error' => 'email_taken']);
    exit;
}

$hash = password_hash($password, PASSWORD_DEFAULT);
$ip = $_SERVER['REMOTE_ADDR'] ?? null;
$referrer = $_SERVER['HTTP_REFERER'] ?? null;
$stmt = $conn->prepare("INSERT INTO users (email, password_hash, signup_ip, signup_referrer) VALUES (?, ?, ?, ?)");
$stmt->bind_param('ssss', $email, $hash, $ip, $referrer);
$stmt->execute();
$user_id = $conn->insert_id;

$session = create_session($conn, $user_id);
echo json_encode(['ok' => true, 'token' => $session['token'], 'expires_at' => $session['expires_at']]);
