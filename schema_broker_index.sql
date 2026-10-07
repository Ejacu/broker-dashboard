-- 在 phpMyAdmin 的 SQL 分頁執行這段,幫「依券商查詢」加一個索引,
-- 不然資料表現在有上百萬筆,沒有索引的話查詢會很慢
ALTER TABLE broker_summary ADD KEY idx_broker_date (broker, trade_date);
