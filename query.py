from sqlalchemy import text
from db import engine

'''
We put queries in query.py, run it with uv run python query.py
Below is an example
'''
with engine.connect() as conn:
    rows = conn.execute(text("SELECT * FROM names"))
    for row in rows:
        print(row._mapping["names"])