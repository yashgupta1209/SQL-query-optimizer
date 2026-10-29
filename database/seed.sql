-- Controlled synthetic workload for Review 2.
-- Increase the multipliers later for Review 3.

INSERT INTO customers (name, city, age)
SELECT
    'Customer ' || g,
    (ARRAY['Delhi','Faridabad','Chennai','Bengaluru','Mumbai','Pune','Hyderabad','Kolkata'])[1 + ((g-1) % 8)],
    18 + ((g * 17) % 73)
FROM generate_series(1, 10000) AS g;

INSERT INTO products (name, category, price)
SELECT
    'Product ' || g,
    (ARRAY['Electronics','Books','Clothing','Home','Sports'])[1 + ((g-1) % 5)],
    round((50 + ((g * 37) % 4950))::numeric, 2)
FROM generate_series(1, 5000) AS g;

INSERT INTO orders (customer_id, order_date, amount, status)
SELECT
    1 + ((g * 7919) % 10000),
    DATE '2023-01-01' + ((g * 13) % 1095),
    round((100 + ((g * 97) % 9900))::numeric, 2),
    (ARRAY['pending','shipped','delivered','cancelled'])[1 + ((g * 7) % 4)]
FROM generate_series(1, 100000) AS g;

INSERT INTO order_items (order_id, product_id, quantity)
SELECT
    1 + ((g * 7919) % 100000),
    1 + ((g * 3571) % 5000),
    1 + ((g * 11) % 5)
FROM generate_series(1, 200000) AS g;

ANALYZE;
