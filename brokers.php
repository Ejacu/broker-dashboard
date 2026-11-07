<?php
require_once __DIR__ . '/auth.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$conn = get_db();
require_auth($conn);
$res = $conn->query("SELECT DISTINCT broker FROM broker_summary ORDER BY broker");

$brokers = [];
while ($row = $res->fetch_assoc()) {
    $brokers[] = $row['broker'];
}

echo json_encode($brokers);
