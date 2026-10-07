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
$detail_records = $payload['detail_records'] ?? [];
$price_records = $payload['price_records'] ?? [];
if ((!is_array($records) || count($records) === 0)
    && (!is_array($detail_records) || count($detail_records) === 0)
    && (!is_array($price_records) || count($price_records) === 0)) {
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

$detail_stmt = $conn->prepare(
    "INSERT INTO broker_price_detail
        (stock_id, trade_date, broker, price, buy_lots, sell_lots)
     VALUES (?, ?, ?, ?, ?, ?)
     ON DUPLICATE KEY UPDATE
        buy_lots = VALUES(buy_lots),
        sell_lots = VALUES(sell_lots)"
);

$detail_inserted = 0;
foreach ($detail_records as $r) {
    $stock_id = (string)($r['stock_id'] ?? '');
    $trade_date = (string)($r['date'] ?? '');
    $broker = (string)($r['broker'] ?? '');
    if ($stock_id === '' || $trade_date === '' || $broker === '') {
        continue;
    }
    $price = (float)($r['price'] ?? 0);
    $buy_lots = (float)($r['buy_lots'] ?? 0);
    $sell_lots = (float)($r['sell_lots'] ?? 0);

    $detail_stmt->bind_param(
        'sssddd',
        $stock_id, $trade_date, $broker,
        $price, $buy_lots, $sell_lots
    );
    $detail_stmt->execute();
    $detail_inserted++;
}

// stock_price_daily 是後來才加的表,用 prepare() 回傳值防一下:
// 萬一哪次忘了先跑 schema_stock_price.sql,這裡頂多略過收盤價,
// 不會讓整支 upload.php(連同既有的分點資料寫入)一起壞掉
$price_stmt = $conn->prepare(
    "INSERT INTO stock_price_daily
        (stock_id, trade_date, open_price, high_price, low_price, close_price, volume_lots, change_val, change_pct)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON DUPLICATE KEY UPDATE
        open_price = VALUES(open_price),
        high_price = VALUES(high_price),
        low_price = VALUES(low_price),
        close_price = VALUES(close_price),
        volume_lots = VALUES(volume_lots),
        change_val = VALUES(change_val),
        change_pct = VALUES(change_pct)"
);

$price_inserted = 0;
if ($price_stmt) {
    foreach ($price_records as $r) {
        $stock_id = (string)($r['stock_id'] ?? '');
        $trade_date = (string)($r['date'] ?? '');
        if ($stock_id === '' || $trade_date === '') {
            continue;
        }
        $open_price = (float)($r['open'] ?? ($r['close'] ?? 0));
        $high_price = (float)($r['high'] ?? ($r['close'] ?? 0));
        $low_price = (float)($r['low'] ?? ($r['close'] ?? 0));
        $close_price = (float)($r['close'] ?? 0);
        $volume_lots = (float)($r['volume'] ?? 0);
        $change_val = (float)($r['change'] ?? 0);
        $change_pct = (float)($r['change_pct'] ?? 0);

        $price_stmt->bind_param(
            'ssddddddd',
            $stock_id, $trade_date,
            $open_price, $high_price, $low_price, $close_price, $volume_lots,
            $change_val, $change_pct
        );
        $price_stmt->execute();
        $price_inserted++;
    }
} elseif (count($price_records) > 0) {
    error_log('upload.php: stock_price_daily 寫入失敗(可能缺欄位或表還沒 ALTER),收盤價資料被略過');
}

echo json_encode(['ok' => true, 'written' => $inserted, 'detail_written' => $detail_inserted, 'price_written' => $price_inserted]);
