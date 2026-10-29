DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    age INT NOT NULL CHECK (age BETWEEN 18 AND 90)
);

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price NUMERIC(10,2) NOT NULL
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(customer_id),
    order_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(order_id),
    product_id INT NOT NULL REFERENCES products(product_id),
    quantity INT NOT NULL
);

CREATE INDEX idx_customers_city ON customers(city);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_amount ON orders(amount);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

-- Feedback storage (objective 7 of Review 2):
-- actual execution results are recorded here and used to retrain the model.
CREATE TABLE IF NOT EXISTS feedback (
    id                  SERIAL PRIMARY KEY,
    query_id            TEXT NOT NULL,
    query_text          TEXT NOT NULL,
    candidate_name      TEXT NOT NULL,
    predicted_runtime_ms DOUBLE PRECISION,
    actual_runtime_ms   DOUBLE PRECISION NOT NULL,
    planning_time_ms    DOUBLE PRECISION,
    ml_selected         BOOLEAN,
    is_actual_best      BOOLEAN,
    model_file          TEXT,
    source              TEXT NOT NULL DEFAULT 'live',
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_query ON feedback(query_id);

ANALYZE;
