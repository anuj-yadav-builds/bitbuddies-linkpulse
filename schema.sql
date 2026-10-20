-- LinkPulse database (MySQL 8 / MariaDB).
-- The app creates these tables by itself on first start.
-- Use this file only if you want to create them by hand.

CREATE DATABASE IF NOT EXISTS linkpulse
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE linkpulse;

CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(80)  NOT NULL,
  email         VARCHAR(120) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role          VARCHAR(10)  NOT NULL DEFAULT 'user',
  created_at    DATETIME     NOT NULL,
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS campaigns (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  name       VARCHAR(80) NOT NULL,
  user_id    INT         NOT NULL,
  created_at DATETIME    NOT NULL,
  CONSTRAINT fk_campaigns_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS urls (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  code          VARCHAR(30)   NOT NULL,
  original_url  VARCHAR(2048) NOT NULL,
  user_id       INT           NULL,
  campaign_id   INT           NULL,
  created_at    DATETIME      NOT NULL,
  expires_at    DATETIME      NULL,
  click_limit   INT           NULL,
  password_hash VARCHAR(255)  NULL,
  disabled      TINYINT(1)    NOT NULL DEFAULT 0,
  tags          VARCHAR(255)  NOT NULL DEFAULT '',
  UNIQUE KEY uq_urls_code (code),
  CONSTRAINT fk_urls_user     FOREIGN KEY (user_id)     REFERENCES users (id),
  CONSTRAINT fk_urls_campaign FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS clicks (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  url_id      INT          NOT NULL,
  clicked_at  DATETIME     NOT NULL,
  ip_hash     VARCHAR(64)  NULL,
  browser     VARCHAR(40)  NULL,
  os_name     VARCHAR(40)  NULL,
  device      VARCHAR(20)  NULL,
  referrer    VARCHAR(255) NULL,
  src         VARCHAR(10)  NULL,
  KEY ix_clicks_url_time (url_id, clicked_at),
  CONSTRAINT fk_clicks_url FOREIGN KEY (url_id) REFERENCES urls (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS blocked_domains (
  id     INT AUTO_INCREMENT PRIMARY KEY,
  domain VARCHAR(120) NOT NULL,
  UNIQUE KEY uq_blocked_domain (domain)
) ENGINE=InnoDB;
