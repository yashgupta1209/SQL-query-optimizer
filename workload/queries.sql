-- Representative Review 2 queries.

-- Q001: filter
SELECT *
FROM customers
WHERE city = 'Delhi';

-- Q002: indexed lookup
SELECT *
FROM orders
WHERE customer_id = 5000;

-- Q003: join
SELECT c.city, COUNT(*)
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.city;

-- Q004: join + filter
SELECT c.city, SUM(o.amount)
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE c.city IN ('Delhi', 'Faridabad')
GROUP BY c.city;

-- Q005: aggregation
SELECT status, AVG(amount)
FROM orders
GROUP BY status;

-- Q006: ordering
SELECT *
FROM orders
WHERE amount > 5000
ORDER BY amount DESC
LIMIT 100;

-- Q007: three-table join
SELECT c.city, p.category, SUM(oi.quantity)
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
GROUP BY c.city, p.category;
