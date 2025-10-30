-- Shift Management Database Schema

-- Create operators table
CREATE TABLE IF NOT EXISTS operators (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    employee_id VARCHAR(50) NOT NULL UNIQUE,
    role ENUM('weigher', 'supervisor', 'admin') NOT NULL DEFAULT 'weigher',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_employee_id (employee_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create shifts table
CREATE TABLE IF NOT EXISTS shifts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    operator_id INT NOT NULL,
    shift_type ENUM('morning', 'afternoon', 'night') NOT NULL,
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    duration_minutes INT NULL,
    transactions_processed INT NOT NULL DEFAULT 0,
    notes TEXT NULL,
    FOREIGN KEY (operator_id) REFERENCES operators(id) ON DELETE CASCADE,
    INDEX idx_operator_id (operator_id),
    INDEX idx_start_time (start_time),
    INDEX idx_end_time (end_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert sample operators
INSERT INTO operators (name, employee_id, role, is_active) VALUES
('John Smith', 'EMP001', 'supervisor', TRUE),
('Sarah Johnson', 'EMP002', 'weigher', TRUE),
('Michael Brown', 'EMP003', 'weigher', TRUE),
('Emily Davis', 'EMP004', 'admin', TRUE)
ON DUPLICATE KEY UPDATE name=VALUES(name);
