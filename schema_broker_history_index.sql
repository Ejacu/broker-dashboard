-- 在 phpMyAdmin 的 SQL 分頁執行這段(記得先在左側選到 sgqvwamy_BROKERDATA 資料庫再執行)
-- 幫「單一股票+單一券商+日期區間」這種查詢模式(range_detail.php,被「分點歷史」跟兩個區間查詢頁共用)加專用索引。
-- 現有索引都是 stock_id, trade_date, broker 這種順序,日期排在券商前面,
-- 範圍查詢(BETWEEN)一出現,後面的 broker 就用不上索引,等於整個區間、全部券商都要掃過一輪。
-- 這個索引把 broker 排到日期前面,讓資料庫可以直接鎖定「這檔股票的這家分點」,不用整段掃描。
--
-- 注意:broker_summary 現在有數千萬筆資料,這個 ALTER 可能要跑幾分鐘。
-- InnoDB 建這種一般索引預設是線上建立(不會整個鎖表),網站其他查詢不會被卡住,但 phpMyAdmin 頁面本身可能會等比較久才跑完,是正常的,不要中途關掉分頁。
ALTER TABLE broker_summary ADD KEY idx_stock_broker_date (stock_id, broker, trade_date);
