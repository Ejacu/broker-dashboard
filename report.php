<?php
// 只給網站管理者自己用的統計報告 API,不是給一般會員用的——
// 用跟自動化腳本一樣的 service_token(UPLOAD_TOKEN)保護,沒有這個 token 就不能查。
// 只跑彙總查詢(COUNT/GROUP BY),不會像整表匯出那樣拖垮連線。
require_once __DIR__ . '/auth.php';
send_cors_headers();
header('Content-Type: application/json; charset=utf-8');

if (!is_valid_service_token()) {
    http_response_code(401);
    echo json_encode(['error' => 'unauthorized']);
    exit;
}

$conn = get_db();
$report = [];

function query_or_fail(mysqli $conn, string $sql) {
    $res = $conn->query($sql);
    if ($res === false) {
        http_response_code(500);
        echo json_encode(['error' => 'query_failed', 'sql' => $sql, 'mysql_error' => $conn->error]);
        exit;
    }
    return $res;
}

$res = query_or_fail($conn, "SELECT COUNT(*) AS c FROM users");
$report['total_users'] = (int)$res->fetch_assoc()['c'];

$res = query_or_fail($conn, "SELECT COUNT(*) AS c FROM users WHERE created_at >= NOW() - INTERVAL 7 DAY");
$report['new_users_7d'] = (int)$res->fetch_assoc()['c'];

$res = query_or_fail($conn, "SELECT COUNT(*) AS c FROM users WHERE created_at >= NOW() - INTERVAL 30 DAY");
$report['new_users_30d'] = (int)$res->fetch_assoc()['c'];

$daily = [];
$res = query_or_fail($conn, "SELECT DATE(created_at) AS d, COUNT(*) AS c FROM users WHERE created_at >= NOW() - INTERVAL 30 DAY GROUP BY d ORDER BY d DESC");
while ($row = $res->fetch_assoc()) {
    $daily[] = ['date' => $row['d'], 'count' => (int)$row['c']];
}
$report['daily_signups_30d'] = $daily;

$res = query_or_fail($conn, "SELECT plan, COUNT(*) AS c FROM users GROUP BY plan");
$plans = [];
while ($row = $res->fetch_assoc()) {
    $plans[$row['plan']] = (int)$row['c'];
}
$report['users_by_plan'] = $plans;

$members = [];
$res = query_or_fail($conn, "SELECT email, plan, created_at, signup_ip, signup_referrer, login_count, last_login_at, last_active_at FROM users ORDER BY created_at DESC");
while ($row = $res->fetch_assoc()) {
    $members[] = $row;
}
$report['members'] = $members;

// 注意:broker_summary 這張表將近 1 億筆,千萬不要在這裡對它做 COUNT(*)/COUNT(DISTINCT)
// 這類全表彙總查詢,共享主機扛不住會逾時(跟 phpMyAdmin #2006 是同一類問題)。
// 股票覆蓋數改由 db_report.py 另外呼叫 stocks.php(已知在這張表上查得快)取得。

echo json_encode($report);
