<?php
require_once __DIR__ . '/config.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$stock = $_GET['stock'] ?? '';
$broker = $_GET['broker'] ?? '';
$start = $_GET['start'] ?? '';
$end = $_GET['end'] ?? '';
if ($stock === '' || $broker === '' || $start === '' || $end === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing_params']);
    exit;
}

$conn = get_db();
$stmt = $conn->prepare(
    "SELECT trade_date, buy_avg, sell_avg, total_buy_lots, total_sell_lots, net_lots
     FROM broker_summary
     WHERE stock_id = ? AND broker = ? AND trade_date BETWEEN ? AND ?
     ORDER BY trade_date"
);
$stmt->bind_param('ssss', $stock, $broker, $start, $end);
$stmt->execute();
$res = $stmt->get_result();

$rows = [];
while ($row = $res->fetch_assoc()) {
    $rows[] = [
        'trade_date' => $row['trade_date'],
        'buy_avg' => round((float)$row['buy_avg'], 2),
        'sell_avg' => round((float)$row['sell_avg'], 2),
        'total_buy_lots' => round((float)$row['total_buy_lots'], 1),
        'total_sell_lots' => round((float)$row['total_sell_lots'], 1),
        'net_lots' => round((float)$row['net_lots'], 1),
    ];
}

echo json_encode(['stock_id' => $stock, 'broker' => $broker, 'start' => $start, 'end' => $end, 'rows' => $rows]);
