-- 在 phpMyAdmin 的 SQL 分頁執行這段(記得先在左側選到 sgqvwamy_BROKERDATA 資料庫再執行)
-- 讓 users 表支援 Google 登入:password_hash 允許空值(Google 帳號沒有密碼),
-- 另外加一欄記錄這個帳號是用哪種方式註冊的,方便之後排查問題。
ALTER TABLE users
    MODIFY password_hash VARCHAR(255) NULL,
    ADD COLUMN auth_provider VARCHAR(20) NOT NULL DEFAULT 'password';
