<?php
require_once __DIR__ . '/config.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$stock_id = $_GET['stock'] ?? '';
$date = $_GET['date'] ?? '';
if ($stock_id === '' || $date === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing_stock_or_date']);
    exit;
}

$conn = get_db();
$stmt = $conn->prepare(
    "SELECT broker, buy_avg, sell_avg, main_avg, net_lots, total_buy_lots, total_sell_lots
     FROM broker_summary
     WHERE stock_id = ? AND trade_date = ?
     ORDER BY net_lots DESC"
);
$stmt->bind_param('ss', $stock_id, $date);
$stmt->execute();
$res = $stmt->get_result();

$summary = [];
while ($row = $res->fetch_assoc()) {
    $net_lots = (float)$row['net_lots'];
    if ($net_lots == 0) {
        continue;
    }
    $summary[] = [
        'broker' => $row['broker'],
        'action' => $net_lots > 0 ? '買超' : '賣超',
        'color' => $net_lots > 0 ? '#E74C3C' : '#27AE60',
        'main_avg' => (float)$row['main_avg'],
        'net_lots' => $net_lots,
        'abs_lots' => abs($net_lots),
        'buy_avg' => (float)$row['buy_avg'],
        'sell_avg' => (float)$row['sell_avg'],
        'total_buy_lots' => (float)$row['total_buy_lots'],
        'total_sell_lots' => (float)$row['total_sell_lots'],
    ];
}

echo json_encode(['stock_id' => $stock_id, 'date' => $date, 'summary' => $summary]);
