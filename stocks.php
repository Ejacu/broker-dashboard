<?php
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
