# PostgreSQL setup

1. Create a database named `sql_optimizer`.
2. Install the Python dependencies from the project root:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set your PostgreSQL password.
4. Run the schema:
   `psql -U postgres -d sql_optimizer -f database/schema.sql`
5. Run the seed:
   `psql -U postgres -d sql_optimizer -f database/seed.sql`

Expected Review 2 dataset size:
- customers: 10,000
- products: 5,000
- orders: 100,000
- order_items: 200,000

For Review 3, increase these sizes and generate a much broader query workload.
