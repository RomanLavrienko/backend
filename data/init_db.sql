-- users
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(15) NOT NULL,
    nickname VARCHAR(10) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(100) NOT NULL,
    specification VARCHAR(100) DEFAULT '',
    description VARCHAR(500),
    created_at DATETIME NOT NULL,
    jwt_token VARCHAR(500),
    email_verified BOOLEAN DEFAULT FALSE,
    last_login DATETIME,
    customer_rating FLOAT DEFAULT 0.0,
    executor_rating FLOAT DEFAULT 0.0,
    done_count INT DEFAULT 0,
    taken_count INT DEFAULT 0,
    photo VARCHAR(255),
    balance FLOAT DEFAULT 0.0,
    is_support BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE COMMENT 'Верификация по номеру телефона',
    admin_verified BOOLEAN DEFAULT FALSE COMMENT 'Верификация администрацией',
    phone_number VARCHAR(20) COMMENT 'Номер телефона в формате E.164',
    INDEX idx_users_created_at (created_at),
    INDEX idx_users_customer_rating (customer_rating),
    INDEX idx_users_executor_rating (executor_rating)
);


-- categories
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- orders
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(30) NOT NULL,
    description VARCHAR(250) NOT NULL,
    price INT NOT NULL,
    customer_id INT NOT NULL,
    responses INT DEFAULT 0,
    term INT NOT NULL,
    created_at DATETIME NOT NULL,
    started_at DATETIME,
    closed_at DATETIME,
    executor_id INT,
    priority ENUM('BASE', 'PREMIUM', 'EXPRESS', 'NEW') DEFAULT 'BASE',
    status ENUM('open', 'close') DEFAULT 'open',
    category_id INT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES users(id),
    FOREIGN KEY (executor_id) REFERENCES users(id),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    INDEX idx_orders_customer_id (customer_id),
    INDEX idx_orders_executor_id (executor_id),
    INDEX idx_orders_category_id (category_id),
    INDEX idx_orders_created_at (created_at),
    INDEX idx_orders_status (status),
    INDEX idx_orders_priority (priority)
);

-- Изменён тип поля status для поддержки длинных статусов
ALTER TABLE orders MODIFY COLUMN status VARCHAR(20) NOT NULL;

-- reviews
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type ENUM('executor', 'customer') NOT NULL,
    rate INT NOT NULL CHECK (rate BETWEEN 1 AND 5),
    text VARCHAR(150) NOT NULL,
    response VARCHAR(100),
    sender_id INT NOT NULL,
    recipient_id INT NOT NULL,
    order_id INT,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (recipient_id) REFERENCES users(id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    INDEX idx_reviews_sender_id (sender_id),
    INDEX idx_reviews_recipient_id (recipient_id),
    INDEX idx_reviews_order_id (order_id),
    INDEX idx_reviews_created_at (created_at),
    INDEX idx_reviews_type (type)
);

-- chats
CREATE TABLE chats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    executor_id INT NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES users(id),
    FOREIGN KEY (executor_id) REFERENCES users(id),
    INDEX idx_chats_customer_id (customer_id),
    INDEX idx_chats_executor_id (executor_id),
    INDEX idx_chats_created_at (created_at)
);

-- messages
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chat_id INT NOT NULL,
    sender_id INT NOT NULL,
    text TEXT NOT NULL,
    type VARCHAR(20),
    created_at DATETIME NOT NULL,
    order_id INT,
    offer_price FLOAT,
    FOREIGN KEY (chat_id) REFERENCES chats(id),
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    INDEX idx_messages_chat_id (chat_id),
    INDEX idx_messages_sender_id (sender_id),
    INDEX idx_messages_created_at (created_at)
);

-- избранные заказы
CREATE TABLE favorite_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    order_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_favorite (user_id, order_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- contact requests
CREATE TABLE contact_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    message VARCHAR(1000) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at DATETIME NOT NULL,
    answered_at DATETIME
);

-- Пример наполнения категорий
INSERT INTO categories (name) VALUES ('Дизайн'), ('Программирование'), ('Копирайтинг'), ('Маркетинг');

CREATE TABLE IF NOT EXISTS commission_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    commission_withdraw FLOAT DEFAULT 3.0,
    commission_customer FLOAT DEFAULT 10.0,
    commission_executor FLOAT DEFAULT 5.0,
    commission_post_order INT DEFAULT 200,
    commission_response_threshold INT DEFAULT 5000,
    commission_response_percent FLOAT DEFAULT 1.0
);