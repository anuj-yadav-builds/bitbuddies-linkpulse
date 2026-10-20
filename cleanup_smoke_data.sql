-- Removes the test users and test links that smoke_test.py creates.
-- Run it before the demo: in MySQL Workbench (select your database first), or
--   mysql -u root -p linkpulse < cleanup_smoke_data.sql
DELETE FROM clicks WHERE url_id IN (SELECT id FROM urls WHERE code LIKE 'smoke%');
DELETE FROM urls WHERE code LIKE 'smoke%';
DELETE FROM campaigns WHERE name LIKE 'Smoke Campaign %';
DELETE FROM blocked_domains WHERE domain LIKE 'smoke-blocked-%';
DELETE FROM users WHERE email LIKE 'smoke%@example.com';
