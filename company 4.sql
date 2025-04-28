-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: mysql
-- Generation Time: Apr 28, 2025 at 02:20 PM
-- Server version: 9.3.0
-- PHP Version: 8.2.27

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `company`
--

-- --------------------------------------------------------

--
-- Table structure for table `images`
--

CREATE TABLE `images` (
  `image_pk` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `image_item_fk` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `image_name` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `images`
--

INSERT INTO `images` (`image_pk`, `image_item_fk`, `image_name`) VALUES
('0a0352a2a3f3437f88dac1b33de7392f', 'db42c04e8c9a456e825e09794d307110', '1b91f6b2c05443fa81d0a8b4c9ce5d30.jpg'),
('0bfc4211ff2c40838bcf658a5cccccc6', 'dd13c6ffd56b40e2a5205db37eaa3b0f', '085fab378bcc47678379113f6478edd2.jpg'),
('c1a3fdaca819414b96d4f397891ad476', '551cc7d73b1041eda764fe925724a45e', 'a06473b5e20a4b57ab729ae6e7a5314f.jpg'),
('c629d7dafd09439b80dcfd3dd1203536', 'fb120f58a85b46ad8119ccc6cd6d08bb', '6d2d9cf18bef42fbb27d8e64bbb9be68.png'),
('df56871b0296423da96d9511acac5847', '0ca3d4760ab84a2ab99dbe5fac49b78c', '5a3ce61208ad4205955fc0a6bb12d151.jpg');

-- --------------------------------------------------------

--
-- Table structure for table `items`
--

CREATE TABLE `items` (
  `item_pk` char(32) NOT NULL,
  `item_user_fk` varchar(32) NOT NULL,
  `item_name` varchar(50) NOT NULL,
  `item_image` varchar(50) NOT NULL,
  `item_price` int UNSIGNED NOT NULL,
  `item_lon` varchar(50) NOT NULL,
  `item_lat` varchar(50) NOT NULL,
  `item_created_at` bigint UNSIGNED NOT NULL,
  `item_deleted_at` bigint UNSIGNED NOT NULL,
  `item_updated_at` bigint UNSIGNED NOT NULL,
  `item_blocked` tinyint(1) NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `items`
--

INSERT INTO `items` (`item_pk`, `item_user_fk`, `item_name`, `item_image`, `item_price`, `item_lon`, `item_lat`, `item_created_at`, `item_deleted_at`, `item_updated_at`, `item_blocked`) VALUES
('0ca3d4760ab84a2ab99dbe5fac49b78c', '7', 'DGI Byen', '5a3ce61208ad4205955fc0a6bb12d151.jpg', 2222, '12.565', '55.6701', 1745841860, 0, 0, 0),
('193e055791ed4fa5a6f24d0ea7422a89', '4', 'Tivoli Gardens #1', '6d2d9cf18bef42fbb27d8e64bbb9be68.png', 220000, '12.5673', '55.6731', 2, 1745844686, 1745844053, 0),
('551cc7d73b1041eda764fe925724a45e', '7', 'Tivoli', 'a06473b5e20a4b57ab729ae6e7a5314f.jpg', 2000, '12.5681', '55.6737', 1745841709, 0, 0, 0),
('56f9d2171b2646f7a077a6ee4a0ce3c9', '4', 'The Little Mermaid Statue', '6d2d9cf18bef42fbb27d8e64bbb9be68.png', 350950, '12.6030', '55.6910', 3, 0, 0, 0),
('b8f0c4a9fa0d4d1c8c38a1d8986e9c7d', '4', 'Nyhavn (Harbor)', '6d2d9cf18bef42fbb27d8e64bbb9be68.png', 100000, '12.5903', '55.6763', 1, 0, 0, 0),
('cf9e4a6d71ea45cba17078df4d7b2516', '4', 'Rosenborg Castle', '6d2d9cf18bef42fbb27d8e64bbb9be68.png', 5000000, '12.5844', '55.6838', 5, 0, 0, 0),
('db42c04e8c9a456e825e09794d307110', '4', 'Hovedbangården', '1b91f6b2c05443fa81d0a8b4c9ce5d30.jpg', 5000, '12.5649', '55.6728', 1745589394, 0, 0, 0),
('dd13c6ffd56b40e2a5205db37eaa3b0f', '4', 'Vesterport st', '085fab378bcc47678379113f6478edd2.jpg', 500000, '12.5621', '55.676', 1745839932, 0, 0, 0),
('f08b6d7c45ff46a0a95cd13b56ab5676', '4', 'Amalienborg Palace', '6d2d9cf18bef42fbb27d8e64bbb9be68.png', 495000, '12.5917', '55.6759', 4, 0, 0, 0),
('fb120f58a85b46ad8119ccc6cd6d08bb', '4', 'Market', '6d2d9cf18bef42fbb27d8e64bbb9be68.png', 230000, '12.5773', '55.6858', 1745584869, 0, 0, 0);

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_pk` bigint UNSIGNED NOT NULL,
  `user_name` varchar(20) NOT NULL,
  `user_last_name` varchar(20) NOT NULL,
  `user_email` varchar(100) NOT NULL,
  `user_username` varchar(20) NOT NULL,
  `user_password` varchar(255) NOT NULL,
  `user_verification_key` varchar(36) DEFAULT NULL,
  `user_verified_at` bigint UNSIGNED NOT NULL DEFAULT '0',
  `user_created_at` bigint UNSIGNED NOT NULL DEFAULT '0',
  `user_updated_at` bigint UNSIGNED NOT NULL DEFAULT '0',
  `user_deleted_at` bigint UNSIGNED NOT NULL DEFAULT '0',
  `user_reset_token` varchar(50) DEFAULT NULL,
  `user_reset_token_expiry` bigint UNSIGNED DEFAULT NULL,
  `user_is_admin` tinyint(1) DEFAULT '0',
  `user_blocked` tinyint(1) DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_pk`, `user_name`, `user_last_name`, `user_email`, `user_username`, `user_password`, `user_verification_key`, `user_verified_at`, `user_created_at`, `user_updated_at`, `user_deleted_at`, `user_reset_token`, `user_reset_token_expiry`, `user_is_admin`, `user_blocked`) VALUES
(3, 'aa', 'aa', 'a@a.com', 'aa', 'scrypt:32768:8:1$HlAULmayU5AKChmB$5383a5f72a43d94d4f4686d8229c2a2a7efa9c760d58d3f31c3d497eefda732b689a4ea2ae7638ed631ccf890c18eb44d8701f16857b15d7606b036eb3e6e308', '6dd95daa-672c-4840-9fad-407fc9fa3568', 1744628889, 1744627461, 0, 1744634125, NULL, NULL, 0, 0),
(4, 'Hans', 'Boegh', 'b@b.com', 'Boegh98', 'scrypt:32768:8:1$dSSjjBtikAbBbHub$436ffcf9923090922102ca77d67e7c085bb0839d78eb3eb55a7322827b2b34994b7834a975ce096e978b342f8b3d58edbb4172e72aa5bcd3316afce5d93d9791', '5af36674-50fc-49da-94c7-b8a63b0aa8c5', 1744634437, 1744634428, 1745839813, 0, NULL, NULL, 1, 0),
(5, 'sgsdg', 'sdgsdg', 'c@c.com', 'dsgsd', 'scrypt:32768:8:1$GttNorzRnXnqe8Gw$a0406e3cc6d1ff31fcb8c13f8f6866cc5c014a7b12f1867a38913874a45f5bb06da5361ff0e26dd9a464e9fb848303671e9e3f4a10bda51e227be5058962f243', 'c2d88833-54b2-48f0-a961-d436375475ea', 1744634821, 1744634813, 0, 1744634835, NULL, NULL, 0, 0),
(6, 'Erik', 'Hansen', 'hansen@hansen.dk', 'Erik1234', 'scrypt:32768:8:1$oT0Zhcw4QpVBpppv$00a1256436effbed6b1c1aab58ffd80d465f02a243e23d33fe744c8e9613383b028862634f7009a8ea5ee4407e8ab4f347b79c1c6e9de443817a116e2f7e57ae', '6c932882-79a5-41ad-95f5-4231b85e9eda', 1745323586, 1745323574, 0, 1745839685, NULL, NULL, 0, 0),
(7, 'sdgsdg', 'sgsdg', 'sdgsdg@sdgsdg.com', 'ssdgsd', 'scrypt:32768:8:1$m38hcuxhzOmVYofg$3de8ef081f8b6eabd56dc79e70dffe2dd936a534b2da3956dd576844ea60d2d8682f83478d828664762d24115108f27521f4fac5efb94d2e509eae0954ea6d83', 'cd720745-90a1-47cf-9f88-594e6c3513f4', 1745334545, 1745334529, 0, 0, NULL, NULL, 0, 0),
(8, 'test', 'test', 'test@test.com', 'test1', 'scrypt:32768:8:1$4RIXbK9kPvonATEy$a6ec624f38c46bc89ad6ec07da36416389039142f6fc9a10c408b6d8f1dbc582764603cf304e69eed4e1e3e5314c4bd2dc081d7aba971505ba17e20e337ef882', '1ec48c77-b645-44a1-bd3f-d48acff63a7b', 1745334662, 1745334642, 0, 0, NULL, NULL, 0, 1),
(9, 'Testing', 'Testing', 'testing2@test.com', 'Testing2', 'scrypt:32768:8:1$8PiipQyiAIWYiOpF$9fcec91097f52a633205477cea4a7a009cb44f441e9cc463e8fd8c1eb3ce110bb19b56725d396ece8f1f810938940f0f3cdc497ba6249579585f9ec4f447bd5d', '678ba650-6aba-45a9-8124-8cd9798af254', 0, 1745589944, 0, 0, NULL, NULL, 0, 0);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `images`
--
ALTER TABLE `images`
  ADD PRIMARY KEY (`image_pk`);

--
-- Indexes for table `items`
--
ALTER TABLE `items`
  ADD PRIMARY KEY (`item_pk`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_pk`),
  ADD UNIQUE KEY `user_email` (`user_email`),
  ADD UNIQUE KEY `user_username` (`user_username`),
  ADD UNIQUE KEY `user_pk` (`user_pk`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `user_pk` bigint UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
