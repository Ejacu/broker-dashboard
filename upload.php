<?php
// GitHub Actions 每日排程(或本機 backfill.py 一次性匯入)呼叫的寫入端點
require_once __DIR__ . '/config.php';

header('Content-Type: application/json; charset=utf-8');

$raw = file_get_contents('php://input');
$payload = json_decode($raw, true);

if (!$payload || !hash_equals(UPLOAD_TOKEN, (string)($payload['token'] ?? ''))) {
    http_response_code(403);
    echo json_encode(['error' => 'invalid_token']);
    exit;
}

$records = $payload['records'] ?? [];
if (!is_array($records) || count($records) === 0) {
    http_response_code(400);
    echo json_encode(['error' => 'no_records']);
    exit;
}

$conn = get_db();
$stmt = $conn->prepare(
    "INSERT INTO broker_summary
        (stock_id, trade_date, broker, buy_avg, sell_avg, main_avg, net_lots, total_buy_lots, total_sell_lots)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON DUPLICATE KEY UPDATE
        buy_avg = VALUES(buy_avg),
        sell_avg = VALUES(sell_avg),
        main_avg = VALUES(main_avg),
        net_lots = VALUES(net_lots),
        total_buy_lots = VALUES(total_buy_lots),
        total_sell_lots = VALUES(total_sell_lots)"
);

$inserted = 0;
foreach ($records as $r) {
    $stock_id = (string)($r['stock_id'] ?? '');
    $trade_date = (string)($r['date'] ?? '');
    $broker = (string)($r['broker'] ?? '');
    if ($stock_id === '' || $trade_date === '' || $broker === '') {
        continue;
    }
    $buy_avg = (float)($r['buy_avg'] ?? 0);
    $sell_avg = (float)($r['sell_avg'] ?? 0);
    $main_avg = (float)($r['main_avg'] ?? 0);
    $net_lots = (float)($r['net_lots'] ?? 0);
    $total_buy_lots = (float)($r['total_buy_lots'] ?? 0);
    $total_sell_lots = (float)($r['total_sell_lots'] ?? 0);

    $stmt->bind_param(
        'sssdddddd',
        $stock_id, $trade_date, $broker,
        $buy_avg, $sell_avg, $main_avg,
        $net_lots, $total_buy_lots, $total_sell_lots
    );
    $stmt->execute();
    $inserted++;
}

echo json_encode(['ok' => true, 'written' => $inserted]);
