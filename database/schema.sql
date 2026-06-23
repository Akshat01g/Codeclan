CREATE DATABASE codeclan_db;
USE codeclan_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    codeforces_handle VARCHAR(50) DEFAULT NULL,
    cf_last_synced DATETIME DEFAULT NULL,
    cf_rating INT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE solved_problems (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    problem_key VARCHAR(20) NOT NULL,
    contest_id INT DEFAULT NULL,
    problem_index VARCHAR(5) DEFAULT NULL,
    problem_name VARCHAR(255) DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uniq_user_problem (user_id, problem_key)
) ENGINE=InnoDB;