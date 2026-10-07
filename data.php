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
$broker_meta = [];
while ($row = $res->fetch_assoc()) {
    $net_lots = round((float)$row['net_lots'], 1);
    $broker_meta[$row['broker']] = [
        'buy_avg' => round((float)$row['buy_avg'], 2),
        'sell_avg' => round((float)$row['sell_avg'], 2),
        'main_avg' => round((float)$row['main_avg'], 2),
        'net_lots' => $net_lots,
        'total_buy_lots' => round((float)$row['total_buy_lots'], 1),
        'total_sell_lots' => round((float)$row['total_sell_lots'], 1),
    ];
    if ($net_lots == 0) {
        continue;
    }
    $summary[] = [
        'broker' => $row['broker'],
        'action' => $net_lots > 0 ? '買超' : '賣超',
        'color' => $net_lots > 0 ? '#E74C3C' : '#27AE60',
        'main_avg' => $broker_meta[$row['broker']]['main_avg'],
        'net_lots' => $net_lots,
        'abs_lots' => round(abs($net_lots), 1),
        'buy_avg' => $broker_meta[$row['broker']]['buy_avg'],
        'sell_avg' => $broker_meta[$row['broker']]['sell_avg'],
        'total_buy_lots' => $broker_meta[$row['broker']]['total_buy_lots'],
        'total_sell_lots' => $broker_meta[$row['broker']]['total_sell_lots'],
    ];
}

$detail_stmt = $conn->prepare(
    "SELECT broker, price, buy_lots, sell_lots
     FROM broker_price_detail
     WHERE stock_id = ? AND trade_date = ?
     ORDER BY broker, price DESC"
);
$detail_stmt->bind_param('ss', $stock_id, $date);
$detail_stmt->execute();
$detail_res = $detail_stmt->get_result();

$broker_details = [];
while ($row = $detail_res->fetch_assoc()) {
    $broker = $row['broker'];
    if (!isset($broker_details[$broker])) {
        $meta = $broker_meta[$broker] ?? [
            'buy_avg' => 0, 'sell_avg' => 0, 'main_avg' => 0,
            'net_lots' => 0, 'total_buy_lots' => 0, 'total_sell_lots' => 0,
        ];
        $broker_details[$broker] = [
            'buy_avg' => $meta['buy_avg'],
            'sell_avg' => $meta['sell_avg'],
            'main_avg' => $meta['main_avg'],
            'net_lots' => $meta['net_lots'],
            'abs_lots' => round(abs($meta['net_lots']), 1),
            'total_buy_lots' => $meta['total_buy_lots'],
            'total_sell_lots' => $meta['total_sell_lots'],
            'prices' => [],
            'buy_lots' => [],
            'sell_lots' => [],
            'net_lots_list' => [],
        ];
    }
    $price = round((float)$row['price'], 2);
    $buy_lots = round((float)$row['buy_lots'], 1);
    $sell_lots = round((float)$row['sell_lots'], 1);
    $broker_details[$broker]['prices'][] = $price;
    $broker_details[$broker]['buy_lots'][] = $buy_lots;
    $broker_details[$broker]['sell_lots'][] = $sell_lots;
    $broker_details[$broker]['net_lots_list'][] = round($buy_lots - $sell_lots, 1);
}

// 當沖贏家:用買均價/賣均價估算每個券商的當沖(當日沖銷)損益。
// 當沖張數取「買張數、賣張數」中較小的一邊(代表當天真正沖掉的部位),
// 成本用 (賣均價+買均價) * 0.3% 估算,不是精確的真實手續費/證交稅,只是概算。
$daytrade = [];
foreach ($broker_meta as $broker => $meta) {
    $matched_lots = min($meta['total_buy_lots'], $meta['total_sell_lots']);
    if ($matched_lots <= 0) {
        continue;
    }
    $shares = $matched_lots * 1000;
    $gross = ($meta['sell_avg'] - $meta['buy_avg']) * $shares;
    $cost = ($meta['sell_avg'] + $meta['buy_avg']) * 0.003 * $shares;
    $net_profit = $gross - $cost;

    $daytrade[] = [
        'broker' => $broker,
        'buy_avg' => $meta['buy_avg'],
        'sell_avg' => $meta['sell_avg'],
        'matched_lots' => round($matched_lots, 1),
        'gross_profit' => round($gross),
        'cost' => round($cost),
        'net_profit' => round($net_profit),
    ];
}
usort($daytrade, function ($a, $b) {
    return $b['net_profit'] <=> $a['net_profit'];
});

// stock_price_daily 是後來才加的表,用 prepare() 回傳值防一下,
// 避免萬一表還沒建好時,把整支 data.php(連分點資料一起)弄壞
$price = null;
$price_stmt = $conn->prepare(
    "SELECT close_price, change_val, change_pct
     FROM stock_price_daily
     WHERE stock_id = ? AND trade_date = ?"
);
if ($price_stmt) {
    $price_stmt->bind_param('ss', $stock_id, $date);
    $price_stmt->execute();
    $price_row = $price_stmt->get_result()->fetch_assoc();
    if ($price_row) {
        $price = [
            'close' => round((float)$price_row['close_price'], 2),
            'change' => round((float)$price_row['change_val'], 2),
            'change_pct' => round((float)$price_row['change_pct'], 2),
        ];
    }
}

echo json_encode([
    'stock_id' => $stock_id,
    'date' => $date,
    'summary' => $summary,
    'broker_details' => $broker_details,
    'daytrade' => $daytrade,
    'price' => $price,
]);
