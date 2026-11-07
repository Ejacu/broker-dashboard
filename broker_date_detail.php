<?php
require_once __DIR__ . '/auth.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$stock_id = $_GET['stock'] ?? '';
$broker = $_GET['broker'] ?? '';
$date = $_GET['date'] ?? '';
if ($stock_id === '' || $broker === '' || $date === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing_params']);
    exit;
}

$conn = get_db();
require_auth_or_free_stock($conn, $stock_id);
$stmt = $conn->prepare(
    "SELECT price, buy_lots, sell_lots
     FROM broker_price_detail
     WHERE stock_id = ? AND broker = ? AND trade_date = ?
     ORDER BY price DESC"
);
$stmt->bind_param('sss', $stock_id, $broker, $date);
$stmt->execute();
$res = $stmt->get_result();

$rows = [];
while ($row = $res->fetch_assoc()) {
    $buy_lots = round((float)$row['buy_lots'], 1);
    $sell_lots = round((float)$row['sell_lots'], 1);
    $rows[] = [
        'price' => round((float)$row['price'], 2),
        'buy_lots' => $buy_lots,
        'sell_lots' => $sell_lots,
        'net_lots' => round($buy_lots - $sell_lots, 1),
    ];
}

echo json_encode(['stock_id' => $stock_id, 'broker' => $broker, 'date' => $date, 'rows' => $rows]);
