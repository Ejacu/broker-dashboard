<?php
require_once __DIR__ . '/config.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$stock_id = $_GET['stock'] ?? '';
$days = isset($_GET['days']) ? (int)$_GET['days'] : 90;
if ($stock_id === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing_stock']);
    exit;
}
if ($days <= 0 || $days > 400) {
    $days = 90;
}

$conn = get_db();
$rows = [];
$stmt = $conn->prepare(
    "SELECT trade_date, open_price, high_price, low_price, close_price, volume_lots, change_val, change_pct
     FROM stock_price_daily
     WHERE stock_id = ?
     ORDER BY trade_date DESC
     LIMIT ?"
);
if ($stmt) {
    $stmt->bind_param('si', $stock_id, $days);
    $stmt->execute();
    $res = $stmt->get_result();
    while ($row = $res->fetch_assoc()) {
        $rows[] = [
            'trade_date' => $row['trade_date'],
            'open' => round((float)$row['open_price'], 2),
            'high' => round((float)$row['high_price'], 2),
            'low' => round((float)$row['low_price'], 2),
            'close' => round((float)$row['close_price'], 2),
            'volume' => round((float)$row['volume_lots'], 1),
            'change' => round((float)$row['change_val'], 2),
            'change_pct' => round((float)$row['change_pct'], 2),
        ];
    }
    $rows = array_reverse($rows);
}

echo json_encode(['stock_id' => $stock_id, 'rows' => $rows]);
