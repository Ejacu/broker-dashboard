<?php
require_once __DIR__ . '/config.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$stock_id = $_GET['stock'] ?? '';
if ($stock_id === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing_stock']);
    exit;
}

$conn = get_db();
$stmt = $conn->prepare("SELECT DISTINCT trade_date FROM broker_summary WHERE stock_id = ? ORDER BY trade_date DESC");
$stmt->bind_param('s', $stock_id);
$stmt->execute();
$res = $stmt->get_result();

$dates = [];
while ($row = $res->fetch_assoc()) {
    $dates[] = $row['trade_date'];
}

echo json_encode($dates);
