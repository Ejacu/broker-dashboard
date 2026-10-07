<?php
require_once __DIR__ . '/config.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$broker = $_GET['broker'] ?? '';
$start = $_GET['start'] ?? '';
$end = $_GET['end'] ?? '';
if ($broker === '' || $start === '' || $end === '') {
    http_response_code(400);
    echo json_encode(['error' => 'missing_params']);
    exit;
}

$conn = get_db();
$stmt = $conn->prepare(
    "SELECT stock_id,
            SUM(total_buy_lots) AS total_buy_lots,
            SUM(total_sell_lots) AS total_sell_lots,
            SUM(net_lots) AS net_lots,
            SUM(buy_avg * total_buy_lots) AS buy_cost,
            SUM(sell_avg * total_sell_lots) AS sell_cost
     FROM broker_summary
     WHERE broker = ? AND trade_date BETWEEN ? AND ?
     GROUP BY stock_id
     ORDER BY net_lots DESC"
);
$stmt->bind_param('sss', $broker, $start, $end);
$stmt->execute();
$res = $stmt->get_result();

$rows = [];
while ($row = $res->fetch_assoc()) {
    $totalBuy = (float)$row['total_buy_lots'];
    $totalSell = (float)$row['total_sell_lots'];
    $rows[] = [
        'stock_id' => $row['stock_id'],
        'buy_avg' => $totalBuy > 0 ? round((float)$row['buy_cost'] / $totalBuy, 2) : 0,
        'sell_avg' => $totalSell > 0 ? round((float)$row['sell_cost'] / $totalSell, 2) : 0,
        'total_buy_lots' => round($totalBuy, 1),
        'total_sell_lots' => round($totalSell, 1),
        'net_lots' => round((float)$row['net_lots'], 1),
    ];
}

echo json_encode(['broker' => $broker, 'start' => $start, 'end' => $end, 'rows' => $rows]);
