<?php
require_once __DIR__ . '/config.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$broker = $_GET['broker'] ?? '';
$date = $_GET['date'] ?? '';
if ($broker === '' || $date === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing_broker_or_date']);
    exit;
}

$conn = get_db();
$stmt = $conn->prepare(
    "SELECT stock_id, buy_avg, sell_avg, main_avg, net_lots, total_buy_lots, total_sell_lots
     FROM broker_summary
     WHERE broker = ? AND trade_date = ?
     ORDER BY net_lots DESC"
);
$stmt->bind_param('ss', $broker, $date);
$stmt->execute();
$res = $stmt->get_result();

$rows = [];
while ($row = $res->fetch_assoc()) {
    $rows[] = [
        'stock_id' => $row['stock_id'],
        'buy_avg' => round((float)$row['buy_avg'], 2),
        'sell_avg' => round((float)$row['sell_avg'], 2),
        'main_avg' => round((float)$row['main_avg'], 2),
        'net_lots' => round((float)$row['net_lots'], 1),
        'total_buy_lots' => round((float)$row['total_buy_lots'], 1),
        'total_sell_lots' => round((float)$row['total_sell_lots'], 1),
    ];
}

echo json_encode(['broker' => $broker, 'date' => $date, 'rows' => $rows]);
