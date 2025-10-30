--
-- Database initialization script
-- The database name is handled by MySQL environment variables in Docker
--

-- --------------------------------------------------------

--
-- Table structure
--

CREATE TABLE IF NOT EXISTS `Provider` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10001 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `Rates` (
  `product_id` varchar(50) NOT NULL,
  `rate` int(11) DEFAULT 0,
  `scope` varchar(50) DEFAULT NULL,
  INDEX idx_scope (scope)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `Trucks` (
  `id` varchar(10) NOT NULL,
  `provider_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  INDEX idx_provider (provider_id),
  FOREIGN KEY (`provider_id`) REFERENCES `Provider`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
--
-- Dumping data
--

/*
INSERT INTO Provider (`name`) VALUES ('ALL'), ('pro1'),
(3, 'pro2');

INSERT INTO Rates (`product_id`, `rate`, `scope`) VALUES ('1', 2, 'ALL'),
(2, 4, 'pro1');

INSERT INTO Trucks (`id`, `provider_id`) VALUES ('134-33-443', 2),
('222-33-111', 1);
*/
