-- =====================================================================================
-- Practice Shop: tables and seed data for Oracle Database 12c or newer.
--
-- Run this while connected as the schema owner (for example SHOP), in SQL*Plus, SQLcl or
-- SQL Developer:      sqlplus shop/your_password@//dbhost:1521/ORCLPDB1 @shop_oracle.sql
--
-- To start again from nothing, run shop_oracle_drop.sql first.
-- The file is plain ASCII; the bullet character in product specs is written with UNISTR.
-- =====================================================================================

-- ===================================================================== TABLES
CREATE TABLE shop_users (
  id             NUMBER(10)          NOT NULL,
  email          VARCHAR2(255)       NOT NULL,
  name           VARCHAR2(100 CHAR)  NOT NULL,
  password_hash  VARCHAR2(64)        NOT NULL,
  CONSTRAINT shop_users_pk PRIMARY KEY (id),
  CONSTRAINT shop_users_email_uq UNIQUE (email)
);

CREATE TABLE shop_tokens (
  token    VARCHAR2(64)  NOT NULL,
  user_id  NUMBER(10)    NOT NULL,
  CONSTRAINT shop_tokens_pk PRIMARY KEY (token),
  CONSTRAINT shop_tokens_user_fk FOREIGN KEY (user_id) REFERENCES shop_users (id)
);

CREATE INDEX shop_tokens_user_ix ON shop_tokens (user_id);

CREATE TABLE shop_products (
  id           NUMBER(10)           NOT NULL,
  name         VARCHAR2(200 CHAR)   NOT NULL,
  category     VARCHAR2(50)         NOT NULL,
  description  VARCHAR2(1000 CHAR),
  specs        VARCHAR2(200 CHAR),
  price        NUMBER(10)           NOT NULL,
  mrp          NUMBER(10)           NOT NULL,
  stock        NUMBER(10)           NOT NULL,
  rating       NUMBER(2,1)          DEFAULT 0 NOT NULL,
  reviews      NUMBER(10)           DEFAULT 0 NOT NULL,
  image        VARCHAR2(200),
  CONSTRAINT shop_products_pk PRIMARY KEY (id),
  CONSTRAINT shop_products_price_ck CHECK (price > 0 AND mrp >= price),
  CONSTRAINT shop_products_stock_ck CHECK (stock >= 0)
);

CREATE INDEX shop_products_category_ix ON shop_products (category);

CREATE TABLE shop_cart_items (
  id          NUMBER(10)  NOT NULL,
  user_id     NUMBER(10)  NOT NULL,
  product_id  NUMBER(10)  NOT NULL,
  quantity    NUMBER(10)  NOT NULL,
  CONSTRAINT shop_cart_items_pk PRIMARY KEY (id),
  CONSTRAINT shop_cart_items_uq UNIQUE (user_id, product_id),
  CONSTRAINT shop_cart_items_user_fk FOREIGN KEY (user_id) REFERENCES shop_users (id),
  CONSTRAINT shop_cart_items_product_fk FOREIGN KEY (product_id) REFERENCES shop_products (id),
  CONSTRAINT shop_cart_items_qty_ck CHECK (quantity > 0)
);

CREATE TABLE shop_coupons (
  code        VARCHAR2(30)  NOT NULL,
  kind        VARCHAR2(10)  NOT NULL,
  amount      NUMBER(10)    NOT NULL,
  min_order   NUMBER(10)    DEFAULT 0 NOT NULL,
  active      NUMBER(1)     DEFAULT 1 NOT NULL,
  expires_at  TIMESTAMP,
  CONSTRAINT shop_coupons_pk PRIMARY KEY (code),
  CONSTRAINT shop_coupons_kind_ck CHECK (kind IN ('percent', 'flat')),
  CONSTRAINT shop_coupons_active_ck CHECK (active IN (0, 1))
);

CREATE TABLE shop_orders (
  id           NUMBER(10)    NOT NULL,
  user_id      NUMBER(10)    NOT NULL,
  subtotal     NUMBER(12)    NOT NULL,
  discount     NUMBER(12)    DEFAULT 0 NOT NULL,
  total        NUMBER(12)    NOT NULL,
  coupon_code  VARCHAR2(30),
  status       VARCHAR2(20)  DEFAULT 'paid' NOT NULL,
  shipping     CLOB,
  created_at   TIMESTAMP     NOT NULL,
  CONSTRAINT shop_orders_pk PRIMARY KEY (id),
  CONSTRAINT shop_orders_user_fk FOREIGN KEY (user_id) REFERENCES shop_users (id),
  CONSTRAINT shop_orders_status_ck CHECK (status IN ('paid', 'cancelled'))
);

CREATE INDEX shop_orders_user_ix ON shop_orders (user_id);

CREATE TABLE shop_order_items (
  id          NUMBER(10)          NOT NULL,
  order_id    NUMBER(10)          NOT NULL,
  product_id  NUMBER(10)          NOT NULL,
  name        VARCHAR2(200 CHAR)  NOT NULL,
  unit_price  NUMBER(10)          NOT NULL,
  quantity    NUMBER(10)          NOT NULL,
  CONSTRAINT shop_order_items_pk PRIMARY KEY (id),
  CONSTRAINT shop_order_items_order_fk FOREIGN KEY (order_id) REFERENCES shop_orders (id),
  CONSTRAINT shop_order_items_product_fk FOREIGN KEY (product_id) REFERENCES shop_products (id)
);

CREATE INDEX shop_order_items_order_ix ON shop_order_items (order_id);

-- The application hands out ids from this table instead of identity columns or sequences,
-- so that "reset to seed data" can restart the numbering (order #1 again) on every Oracle version.
CREATE TABLE shop_id_counters (
  name      VARCHAR2(30)  NOT NULL,
  next_val  NUMBER(10)    NOT NULL,
  CONSTRAINT shop_id_counters_pk PRIMARY KEY (name)
);

-- ===================================================================== SEED DATA
INSERT INTO shop_users (id, email, name, password_hash) VALUES (1, 'alice@example.com', 'Alice', '1a58544208648e60ce3cd5e1ef5fdc440644ae0d0e6e34d1868f90c77a9fe842');
INSERT INTO shop_users (id, email, name, password_hash) VALUES (2, 'bob@example.com', 'Bob', '1a58544208648e60ce3cd5e1ef5fdc440644ae0d0e6e34d1868f90c77a9fe842');

INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (1, 'Trail Running Shoes', 'sports', 'Trail Running Shoes. Grip sole, Waterproof.', UNISTR('Grip sole \2022 Waterproof'), 2799, 3499, 12, 4.4, 1320, 'shoe');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (2, 'Road Running Shoes', 'sports', 'Road Running Shoes. Lightweight, Cushioned.', UNISTR('Lightweight \2022 Cushioned'), 3499, 3999, 8, 4.5, 2100, 'shoe');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (3, 'Budget Running Shoes', 'sports', 'Budget Running Shoes. Mesh upper, Daily wear.', UNISTR('Mesh upper \2022 Daily wear'), 1499, 1999, 20, 4.0, 640, 'shoe');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (4, 'Leather Formal Shoes', 'fashion', 'Leather Formal Shoes. Genuine leather, Lace-up.', UNISTR('Genuine leather \2022 Lace-up'), 4299, 4999, 5, 4.2, 310, 'shoe');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (5, 'Cotton T-Shirt', 'fashion', 'Cotton T-Shirt. 100% cotton, Regular fit.', UNISTR('100% cotton \2022 Regular fit'), 499, 599, 50, 4.1, 5400, 'shirt');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (6, 'Denim Jacket', 'fashion', 'Denim Jacket. Mid wash, Slim fit.', UNISTR('Mid wash \2022 Slim fit'), 2199, 2999, 7, 4.3, 780, 'shirt');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (7, 'Wireless Earbuds', 'electronics', 'Wireless Earbuds. Active Noise Cancellation.', 'Active Noise Cancellation', 1999, 2399, 15, 4.5, 1600, 'earbuds');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (8, 'Bluetooth Speaker', 'electronics', 'Bluetooth Speaker. Bluetooth 5.3, 12H Playtime.', UNISTR('Bluetooth 5.3 \2022 12H Playtime'), 2499, 2999, 0, 4.4, 980, 'speaker');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (9, 'Phone Case', 'mobiles', 'Phone Case. Shockproof, Slim.', UNISTR('Shockproof \2022 Slim'), 299, 399, 100, 4.0, 8900, 'phone');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (10, 'Steel Water Bottle', 'home', 'Steel Water Bottle. 1 litre, Insulated.', UNISTR('1 litre \2022 Insulated'), 649, 799, 2, 4.6, 450, 'bottle');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (11, 'Smartphone X1', 'mobiles', 'Smartphone X1. 128GB, 5G, AMOLED.', UNISTR('128GB \2022 5G \2022 AMOLED'), 49999, 55999, 9, 4.6, 2800, 'phone');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (12, 'Laptop Pro 15', 'electronics', 'Laptop Pro 15. Intel i5, 8GB, 512GB SSD.', UNISTR('Intel i5 \2022 8GB \2022 512GB SSD'), 42990, 50990, 6, 4.5, 1200, 'laptop');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (13, 'Smart Watch', 'electronics', 'Smart Watch. Heart Rate, SpO2, GPS.', UNISTR('Heart Rate \2022 SpO2 \2022 GPS'), 6999, 8499, 14, 4.3, 1100, 'watch');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (14, 'Noise Cancelling Headphones', 'electronics', 'Noise Cancelling Headphones. Hi-Fi Sound, 40H Playtime.', UNISTR('Hi-Fi Sound \2022 40H Playtime'), 7999, 9299, 10, 4.6, 850, 'headphones');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (15, 'Budget Phone M2', 'mobiles', 'Budget Phone M2. 64GB, 4G, 5000mAh.', UNISTR('64GB \2022 4G \2022 5000mAh'), 9999, 11999, 25, 4.1, 3900, 'phone');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (16, 'Smart TV 43 inch', 'appliances', 'Smart TV 43 inch. 4K UHD, HDR, 3 HDMI.', UNISTR('4K UHD \2022 HDR \2022 3 HDMI'), 19999, 27999, 4, 4.4, 2250, 'tv');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (17, 'Front Load Washing Machine', 'appliances', 'Front Load Washing Machine. 7 kg, 1200 RPM.', UNISTR('7 kg \2022 1200 RPM'), 24990, 31990, 3, 4.3, 610, 'washer');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (18, 'Mixer Grinder', 'appliances', 'Mixer Grinder. 750W, 3 jars.', UNISTR('750W \2022 3 jars'), 2899, 3999, 18, 4.2, 1900, 'mixer');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (19, 'Face Moisturiser', 'beauty', 'Face Moisturiser. 100 ml, All skin types.', UNISTR('100 ml \2022 All skin types'), 349, 449, 60, 4.3, 2700, 'jar');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (20, 'Matte Lipstick', 'beauty', 'Matte Lipstick. Long lasting, Ruby red.', UNISTR('Long lasting \2022 Ruby red'), 499, 599, 40, 4.1, 1500, 'lipstick');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (21, 'Table Lamp', 'home', 'Table Lamp. LED, 3 brightness levels.', UNISTR('LED \2022 3 brightness levels'), 899, 1299, 11, 4.2, 330, 'lamp');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (22, 'Cotton Bedsheet', 'home', 'Cotton Bedsheet. Double, 2 pillow covers.', UNISTR('Double \2022 2 pillow covers'), 1199, 1799, 16, 4.0, 720, 'bed');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (23, 'Building Blocks Set', 'toys', 'Building Blocks Set. 250 pieces, Ages 5+.', UNISTR('250 pieces \2022 Ages 5+'), 1299, 1599, 22, 4.7, 940, 'blocks');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (24, 'Teddy Bear', 'toys', 'Teddy Bear. 40 cm, Soft plush.', UNISTR('40 cm \2022 Soft plush'), 599, 799, 30, 4.5, 1250, 'teddy');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (25, 'Basmati Rice 5kg', 'food', 'Basmati Rice 5kg. Aged, Long grain.', UNISTR('Aged \2022 Long grain'), 649, 749, 45, 4.4, 6100, 'bowl');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (26, 'Dark Chocolate Box', 'food', 'Dark Chocolate Box. 70% cocoa, 12 pieces.', UNISTR('70% cocoa \2022 12 pieces'), 399, 499, 35, 4.6, 2050, 'choc');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (27, 'Cricket Bat', 'sports', 'Cricket Bat. Kashmir willow, Full size.', UNISTR('Kashmir willow \2022 Full size'), 1899, 2499, 9, 4.2, 560, 'bat');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (28, 'Yoga Mat', 'sports', 'Yoga Mat. 6 mm, Anti-slip.', UNISTR('6 mm \2022 Anti-slip'), 799, 999, 28, 4.4, 3100, 'mat');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (29, 'Mystery Novel', 'books', 'Mystery Novel. Paperback, 320 pages.', UNISTR('Paperback \2022 320 pages'), 299, 399, 33, 4.3, 870, 'book');
INSERT INTO shop_products (id, name, category, description, specs, price, mrp, stock, rating, reviews, image) VALUES (30, 'Python Programming Guide', 'books', 'Python Programming Guide. Paperback, 480 pages.', UNISTR('Paperback \2022 480 pages'), 549, 699, 13, 4.5, 410, 'book');

INSERT INTO shop_coupons (code, kind, amount, min_order, active, expires_at) VALUES ('WELCOME10', 'percent', 10, 0, 1, NULL);
INSERT INTO shop_coupons (code, kind, amount, min_order, active, expires_at) VALUES ('FLAT200', 'flat', 200, 1500, 1, NULL);
INSERT INTO shop_coupons (code, kind, amount, min_order, active, expires_at) VALUES ('EXPIRED50', 'percent', 50, 0, 1, TIMESTAMP '2020-01-01 00:00:00');
INSERT INTO shop_coupons (code, kind, amount, min_order, active, expires_at) VALUES ('DISABLED20', 'percent', 20, 0, 0, NULL);

INSERT INTO shop_id_counters (name, next_val) VALUES ('users', 3);
INSERT INTO shop_id_counters (name, next_val) VALUES ('orders', 1);
INSERT INTO shop_id_counters (name, next_val) VALUES ('order_items', 1);
INSERT INTO shop_id_counters (name, next_val) VALUES ('cart_items', 1);

COMMIT;
