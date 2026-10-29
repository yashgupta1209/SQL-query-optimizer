# workload/queries.py

QUERIES = []

# ============================================================
# CONSTANTS MATCHING OUR SEEDED DATABASE
# ============================================================

CITIES = [
    "Delhi",
    "Faridabad",
    "Mumbai",
    "Chennai",
    "Bangalore",
    "Hyderabad",
    "Kolkata",
    "Pune",
    "Jaipur",
    "Lucknow",
]

CUSTOMER_IDS = [
    100,
    500,
    1000,
    1500,
    2000,
    2500,
    3000,
    3500,
    4000,
    4500,
    5000,
    5500,
    6000,
    6500,
    7000,
    7500,
    8000,
    8500,
    9000,
    9500,
]

AMOUNT_THRESHOLDS = [
    500,
    1000,
    1500,
    2000,
    2500,
    3000,
    3500,
    4000,
    4500,
    5000,
    5500,
    6000,
    6500,
    7000,
    7500,
    8000,
    8500,
    9000,
]

LIMITS = [
    10,
    25,
    50,
    100,
    200,
    500,
]


def add_query(query_id, sql):
    QUERIES.append((query_id, sql.strip()))


# ============================================================
# TYPE 1: CUSTOMER FILTER QUERIES
# ============================================================

counter = 1

for city in CITIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT *
        FROM customers
        WHERE city = '{city}';
        """
    )
    counter += 1


# ============================================================
# TYPE 2: CUSTOMER FILTER + ORDER BY
# ============================================================

for city in CITIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT customer_id, city
        FROM customers
        WHERE city = '{city}'
        ORDER BY customer_id;
        """
    )
    counter += 1


# ============================================================
# TYPE 3: CUSTOMER FILTER + LIMIT
# ============================================================

for city in CITIES:
    for limit in LIMITS[:5]:
        add_query(
            f"Q{counter:03d}",
            f"""
            SELECT *
            FROM customers
            WHERE city = '{city}'
            LIMIT {limit};
            """
        )
        counter += 1


# ============================================================
# TYPE 4: ORDER FILTER BY CUSTOMER ID
# ============================================================

for customer_id in CUSTOMER_IDS:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT *
        FROM orders
        WHERE customer_id = {customer_id};
        """
    )
    counter += 1


# ============================================================
# TYPE 5: ORDER FILTER BY CUSTOMER + AMOUNT
# ============================================================

for i, customer_id in enumerate(CUSTOMER_IDS[:20]):
    threshold = AMOUNT_THRESHOLDS[i % len(AMOUNT_THRESHOLDS)]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT *
        FROM orders
        WHERE customer_id = {customer_id}
          AND amount > {threshold};
        """
    )
    counter += 1


# ============================================================
# TYPE 6: ORDER AMOUNT FILTER
# ============================================================

for threshold in AMOUNT_THRESHOLDS:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT *
        FROM orders
        WHERE amount > {threshold};
        """
    )
    counter += 1


# ============================================================
# TYPE 7: ORDER AMOUNT FILTER + ORDER BY
# ============================================================

for threshold in AMOUNT_THRESHOLDS:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT *
        FROM orders
        WHERE amount > {threshold}
        ORDER BY amount DESC;
        """
    )
    counter += 1


# ============================================================
# TYPE 8: ORDER AMOUNT + ORDER BY + LIMIT
# ============================================================

for threshold in AMOUNT_THRESHOLDS:
    for limit in LIMITS:
        add_query(
            f"Q{counter:03d}",
            f"""
            SELECT *
            FROM orders
            WHERE amount > {threshold}
            ORDER BY amount DESC
            LIMIT {limit};
            """
        )
        counter += 1


# ============================================================
# TYPE 9: ORDER STATUS GROUP BY
# ============================================================

STATUSES = [
    "Pending",
    "Completed",
    "Cancelled",
    "Shipped",
]

for status in STATUSES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT status, COUNT(*), AVG(amount), SUM(amount)
        FROM orders
        WHERE status = '{status}'
        GROUP BY status;
        """
    )
    counter += 1


# ============================================================
# TYPE 10: ORDER GROUP BY STATUS
# ============================================================

add_query(
    f"Q{counter:03d}",
    """
    SELECT status, COUNT(*)
    FROM orders
    GROUP BY status;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT status, AVG(amount)
    FROM orders
    GROUP BY status;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT status, SUM(amount)
    FROM orders
    GROUP BY status;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT status, MIN(amount), MAX(amount)
    FROM orders
    GROUP BY status;
    """
)
counter += 1


# ============================================================
# TYPE 11: CUSTOMER + ORDER JOIN
# ============================================================

for city in CITIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, COUNT(*)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        WHERE c.city = '{city}'
        GROUP BY c.city;
        """
    )
    counter += 1


# ============================================================
# TYPE 12: CUSTOMER + ORDER SUM
# ============================================================

for city in CITIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, SUM(o.amount)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        WHERE c.city = '{city}'
        GROUP BY c.city;
        """
    )
    counter += 1


# ============================================================
# TYPE 13: CUSTOMER + ORDER AVG
# ============================================================

for city in CITIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, AVG(o.amount)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        WHERE c.city = '{city}'
        GROUP BY c.city;
        """
    )
    counter += 1


# ============================================================
# TYPE 14: CUSTOMER + ORDER MAX/MIN
# ============================================================

for city in CITIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, MAX(o.amount), MIN(o.amount)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        WHERE c.city = '{city}'
        GROUP BY c.city;
        """
    )
    counter += 1


# ============================================================
# TYPE 15: CUSTOMER + ORDER WITH AMOUNT FILTER
# ============================================================

for i, city in enumerate(CITIES):
    threshold = AMOUNT_THRESHOLDS[(i * 2) % len(AMOUNT_THRESHOLDS)]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, COUNT(*), SUM(o.amount)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        WHERE c.city = '{city}'
          AND o.amount > {threshold}
        GROUP BY c.city;
        """
    )
    counter += 1


# ============================================================
# TYPE 16: CUSTOMER + ORDER GROUP BY ALL CITIES
# ============================================================

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, COUNT(*)
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    GROUP BY c.city;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, SUM(o.amount)
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    GROUP BY c.city;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, AVG(o.amount)
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    GROUP BY c.city;
    """
)
counter += 1


# ============================================================
# TYPE 17: CUSTOMER + ORDER GROUP + ORDER BY
# ============================================================

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, COUNT(*) AS order_count
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    GROUP BY c.city
    ORDER BY order_count DESC;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, SUM(o.amount) AS total_amount
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    GROUP BY c.city
    ORDER BY total_amount DESC;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, AVG(o.amount) AS average_amount
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    GROUP BY c.city
    ORDER BY average_amount DESC;
    """
)
counter += 1


# ============================================================
# TYPE 18: PRODUCTS FILTER
# ============================================================

CATEGORIES = [
    "Electronics",
    "Clothing",
    "Books",
    "Home",
    "Sports",
]

for category in CATEGORIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT *
        FROM products
        WHERE category = '{category}';
        """
    )
    counter += 1


# ============================================================
# TYPE 19: PRODUCTS + ORDER_ITEMS JOIN
# ============================================================

for category in CATEGORIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT p.category, COUNT(*), SUM(oi.quantity)
        FROM products p
        JOIN order_items oi
          ON p.product_id = oi.product_id
        WHERE p.category = '{category}'
        GROUP BY p.category;
        """
    )
    counter += 1


# ============================================================
# TYPE 20: PRODUCT AGGREGATION
# ============================================================

add_query(
    f"Q{counter:03d}",
    """
    SELECT p.category, COUNT(*)
    FROM products p
    JOIN order_items oi
      ON p.product_id = oi.product_id
    GROUP BY p.category;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT p.category, SUM(oi.quantity)
    FROM products p
    JOIN order_items oi
      ON p.product_id = oi.product_id
    GROUP BY p.category;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT p.category, AVG(oi.quantity)
    FROM products p
    JOIN order_items oi
      ON p.product_id = oi.product_id
    GROUP BY p.category;
    """
)
counter += 1


# ============================================================
# TYPE 21: THREE TABLE JOIN
# ============================================================

for city in CITIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, SUM(oi.quantity)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        JOIN order_items oi
          ON o.order_id = oi.order_id
        WHERE c.city = '{city}'
        GROUP BY c.city;
        """
    )
    counter += 1


# ============================================================
# TYPE 22: THREE TABLE JOIN + AMOUNT
# ============================================================

for i, city in enumerate(CITIES):
    threshold = AMOUNT_THRESHOLDS[i + 3]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, SUM(oi.quantity), SUM(o.amount)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        JOIN order_items oi
          ON o.order_id = oi.order_id
        WHERE c.city = '{city}'
          AND o.amount > {threshold}
        GROUP BY c.city;
        """
    )
    counter += 1


# ============================================================
# TYPE 23: THREE TABLE GROUPING
# ============================================================

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, o.status, COUNT(*)
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    JOIN order_items oi
      ON o.order_id = oi.order_id
    GROUP BY c.city, o.status;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, o.status, SUM(oi.quantity)
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    JOIN order_items oi
      ON o.order_id = oi.order_id
    GROUP BY c.city, o.status;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT o.status, SUM(oi.quantity), AVG(o.amount)
    FROM orders o
    JOIN order_items oi
      ON o.order_id = oi.order_id
    GROUP BY o.status;
    """
)
counter += 1


# ============================================================
# TYPE 24: FOUR TABLE JOIN
# ============================================================

for city in CITIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, p.category, SUM(oi.quantity)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        JOIN order_items oi
          ON o.order_id = oi.order_id
        JOIN products p
          ON oi.product_id = p.product_id
        WHERE c.city = '{city}'
        GROUP BY c.city, p.category;
        """
    )
    counter += 1


# ============================================================
# TYPE 25: FOUR TABLE JOIN + CATEGORY
# ============================================================

for category in CATEGORIES:
    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, p.category, SUM(oi.quantity)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        JOIN order_items oi
          ON o.order_id = oi.order_id
        JOIN products p
          ON oi.product_id = p.product_id
        WHERE p.category = '{category}'
        GROUP BY c.city, p.category;
        """
    )
    counter += 1


# ============================================================
# TYPE 26: FOUR TABLE JOIN + CITY + CATEGORY
# ============================================================

for i in range(10):
    city = CITIES[i]
    category = CATEGORIES[i % len(CATEGORIES)]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, p.category, SUM(oi.quantity), AVG(o.amount)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        JOIN order_items oi
          ON o.order_id = oi.order_id
        JOIN products p
          ON oi.product_id = p.product_id
        WHERE c.city = '{city}'
          AND p.category = '{category}'
        GROUP BY c.city, p.category;
        """
    )
    counter += 1


# ============================================================
# TYPE 27: FOUR TABLE JOIN + ORDER AMOUNT
# ============================================================

for i in range(10):
    city = CITIES[i]
    threshold = AMOUNT_THRESHOLDS[i]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, p.category, SUM(oi.quantity)
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        JOIN order_items oi
          ON o.order_id = oi.order_id
        JOIN products p
          ON oi.product_id = p.product_id
        WHERE c.city = '{city}'
          AND o.amount > {threshold}
        GROUP BY c.city, p.category;
        """
    )
    counter += 1


# ============================================================
# TYPE 28: FOUR TABLE JOIN + ORDER BY
# ============================================================

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, p.category, SUM(oi.quantity) AS total_quantity
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    JOIN order_items oi
      ON o.order_id = oi.order_id
    JOIN products p
      ON oi.product_id = p.product_id
    GROUP BY c.city, p.category
    ORDER BY total_quantity DESC;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, p.category, AVG(o.amount) AS avg_amount
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    JOIN order_items oi
      ON o.order_id = oi.order_id
    JOIN products p
      ON oi.product_id = p.product_id
    GROUP BY c.city, p.category
    ORDER BY avg_amount DESC;
    """
)
counter += 1


# ============================================================
# TYPE 29: DIFFERENT JOIN AGGREGATIONS
# ============================================================

add_query(
    f"Q{counter:03d}",
    """
    SELECT p.category, COUNT(DISTINCT o.order_id)
    FROM products p
    JOIN order_items oi
      ON p.product_id = oi.product_id
    JOIN orders o
      ON oi.order_id = o.order_id
    GROUP BY p.category;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, COUNT(DISTINCT o.order_id)
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    GROUP BY c.city;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city, COUNT(DISTINCT p.product_id)
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    JOIN order_items oi
      ON o.order_id = oi.order_id
    JOIN products p
      ON oi.product_id = p.product_id
    GROUP BY c.city;
    """
)
counter += 1


# ============================================================
# TYPE 30: LARGE AGGREGATION QUERIES
# ============================================================

add_query(
    f"Q{counter:03d}",
    """
    SELECT c.city,
           p.category,
           COUNT(*) AS item_count,
           SUM(oi.quantity) AS total_quantity,
           AVG(o.amount) AS avg_amount,
           MAX(o.amount) AS max_amount
    FROM customers c
    JOIN orders o
      ON c.customer_id = o.customer_id
    JOIN order_items oi
      ON o.order_id = oi.order_id
    JOIN products p
      ON oi.product_id = p.product_id
    GROUP BY c.city, p.category;
    """
)
counter += 1

add_query(
    f"Q{counter:03d}",
    """
    SELECT o.status,
           p.category,
           COUNT(*) AS item_count,
           SUM(oi.quantity) AS total_quantity,
           AVG(o.amount) AS avg_amount
    FROM orders o
    JOIN order_items oi
      ON o.order_id = oi.order_id
    JOIN products p
      ON oi.product_id = p.product_id
    GROUP BY o.status, p.category;
    """
)
counter += 1


# ============================================================
# TYPE 31: MULTI-CONDITION CUSTOMER QUERIES
# ============================================================

for i in range(10):
    city1 = CITIES[i]
    city2 = CITIES[(i + 1) % len(CITIES)]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT *
        FROM customers
        WHERE city IN ('{city1}', '{city2}');
        """
    )
    counter += 1


# ============================================================
# TYPE 32: MULTI-CONDITION ORDER QUERIES
# ============================================================

for i in range(15):
    threshold1 = AMOUNT_THRESHOLDS[i]
    threshold2 = AMOUNT_THRESHOLDS[i + 3]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT *
        FROM orders
        WHERE amount > {threshold1}
          AND amount < {threshold2 + 1000};
        """
    )
    counter += 1


# ============================================================
# TYPE 33: MULTI-CONDITION ORDER + SORT
# ============================================================

for i in range(10):
    threshold = AMOUNT_THRESHOLDS[i + 2]
    limit = LIMITS[i % len(LIMITS)]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT order_id, customer_id, amount, status
        FROM orders
        WHERE amount > {threshold}
        ORDER BY amount DESC
        LIMIT {limit};
        """
    )
    counter += 1


# ============================================================
# TYPE 34: CUSTOMER/ORDER JOIN WITH LIMIT
# ============================================================

for i in range(10):
    city = CITIES[i]
    limit = LIMITS[i % len(LIMITS)]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city, o.order_id, o.amount
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        WHERE c.city = '{city}'
        ORDER BY o.amount DESC
        LIMIT {limit};
        """
    )
    counter += 1


# ============================================================
# TYPE 35: FOUR TABLE JOIN WITH LIMIT
# ============================================================

for i in range(10):
    city = CITIES[i]
    limit = LIMITS[i % len(LIMITS)]

    add_query(
        f"Q{counter:03d}",
        f"""
        SELECT c.city,
               p.category,
               oi.quantity,
               o.amount
        FROM customers c
        JOIN orders o
          ON c.customer_id = o.customer_id
        JOIN order_items oi
          ON o.order_id = oi.order_id
        JOIN products p
          ON oi.product_id = p.product_id
        WHERE c.city = '{city}'
        ORDER BY o.amount DESC
        LIMIT {limit};
        """
    )
    counter += 1


# ============================================================
# SAFETY CHECK
# ============================================================

if len(QUERIES) < 250:
    raise RuntimeError(
        f"Expected at least 250 queries, but generated {len(QUERIES)}."
    )