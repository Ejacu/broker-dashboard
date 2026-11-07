<?php
require_once __DIR__ . '/config.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$raw = file_get_contents('php://input');
$payload = json_decode($raw, true) ?: $_POST;
$token = (string)($payload['token'] ?? '');

if ($token !== '') {
    $conn = get_db();
    $stmt = $conn->prepare("DELETE FROM sessions WHERE token = ?");
    $stmt->bind_param('s', $token);
    $stmt->execute();
}

echo json_encode(['ok' => true]);
