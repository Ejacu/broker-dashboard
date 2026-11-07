<?php
// 股票代號清單本身不是機密資料(只是索引,不是細部籌碼),不需要登入就能查,
// 這樣首頁的搜尋自動完成、以及免費試看股票的頁面才能正常運作
require_once __DIR__ . '/config.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');
// 不能被 Bluehost nginx 代理快取 24 小時,否則 expand_universe.py 看到的「已追蹤股票」是舊的,會重複補同一批
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('X-Accel-Expires: 0');

$conn = get_db();
$res = $conn->query("SELECT DISTINCT stock_id FROM broker_summary ORDER BY stock_id");

$stocks = [];
while ($row = $res->fetch_assoc()) {
    $stocks[] = $row['stock_id'];
}

echo json_encode($stocks);
