
-- ================================================================
-- VergeGrid Standalone Schema (Modular, OpenSim-safe)
-- ================================================================

CREATE SCHEMA IF NOT EXISTS vergegrid DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE vergegrid;

-- Table: Nodes
CREATE TABLE IF NOT EXISTS vergegrid.vg_nodes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    node_uuid CHAR(36) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    api_key VARCHAR(128) NOT NULL,
    endpoint_url VARCHAR(255),
    status ENUM('active', 'inactive', 'quarantined') DEFAULT 'inactive',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table: Regions
CREATE TABLE IF NOT EXISTS vergegrid.vg_regions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    region_uuid CHAR(36) NOT NULL UNIQUE,
    sim_uuid CHAR(36) NOT NULL,
    name VARCHAR(128),
    template_version VARCHAR(32),
    state ENUM('active', 'stopped', 'deleted') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table: Trust Scores
CREATE TABLE IF NOT EXISTS vergegrid.vg_trust_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    node_uuid CHAR(36) NOT NULL,
    trust_score FLOAT DEFAULT 1.0,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (node_uuid) REFERENCES vergegrid.vg_nodes(node_uuid) ON DELETE CASCADE
);

-- Table: Keys
CREATE TABLE IF NOT EXISTS vergegrid.vg_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    node_uuid CHAR(36) NOT NULL,
    public_key TEXT NOT NULL,
    key_hash CHAR(64) NOT NULL,
    rotation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (node_uuid) REFERENCES vergegrid.vg_nodes(node_uuid) ON DELETE CASCADE
);

-- Table: User Roles
CREATE TABLE IF NOT EXISTS vergegrid.vg_user_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id CHAR(36) NOT NULL,
    role ENUM('admin', 'operator', 'viewer') DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_role (user_id),
    INDEX (role)
);

-- Table: Audit Log
CREATE TABLE IF NOT EXISTS vergegrid.vg_audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(128),
    message TEXT,
    actor_id CHAR(36),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    encrypted BOOLEAN DEFAULT FALSE
);
