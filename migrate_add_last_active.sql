-- 在 phpMyAdmin 的 SQL 分頁執行這段(記得先點進左側的 sgqvwamy_BROKERDATA,再點 SQL 分頁,
-- 不要在「伺服器」層級執行,不然會出現 #1046 - No database selected)
-- users 表筆數很少,瞬間完成。

ALTER TABLE users
    ADD COLUMN last_active_at DATETIME NULL;
