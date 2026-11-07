<?php
// 股票代號清單本身不是機密資料(只是索引,不是細部籌碼),不需要登入就能查,
// 這樣首頁的搜尋自動完成、以及免費試看股票的頁面才能正常運作
require_once __DIR__ . '/config.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

$conn = get_db();
$res = $conn->query("SELECT DISTINCT stock_id FROM broker_summary ORDER BY stock_id");

$stocks = [];
while ($row = $res->fetch_assoc()) {
    $stocks[] = $row['stock_id'];
}

echo json_encode($stocks);
