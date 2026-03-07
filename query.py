from sqlalchemy import text
from sqlalchemy.engine import Engine
from typing import List, Dict, Any, Tuple
from datetime import date


def communes_per_department(engine: Engine) -> List[Dict[str, Any]]:
    """
    Q1: The number of communes per department
    Returns: [{"dept_code": "...", "total_town": N}, ...]
    """
    sql = text("""
        SELECT dept_code, COUNT(*) AS total_town
        FROM town
        GROUP BY dept_code;
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).all()
        return [dict(r._mapping) for r in rows]


def acts_in_town(engine: Engine) -> int:
    """
    Q2: The number of acts in Luçon
    Returns: integer
    """
    sql = text("""
        SELECT COUNT(*)
        FROM act
        JOIN town ON act.town_id = town.id
        WHERE town.name ~* '^LUÇON$';
    """)
    with engine.connect() as conn:
        return conn.execute(sql).scalar_one()


def marriage_contracts_before_1855(engine: Engine) -> int:
    """
    Q3 : The number of marriage contracts before 1855
    Return: integer
    """
    sql = text("""
        SELECT COUNT(*)
        FROM act
        WHERE act.act_type = 'Contrat de mariage'
        AND act.act_date < '1855-01-01';
        """)
    with engine.connect() as conn:
        return conn.execute(sql).scalar_one()
    

def town_highest_number_marriage_pub(engine: Engine) -> str:
    """
    Q4 : The town with the highest number of marriage publications
    Return: string
    """
    sql = text("""
        SELECT town.name, COUNT(*) AS total_publications
        FROM act
        JOIN town ON act.town_id = town.id
        WHERE act.act_type = 'Publication de mariage'
        GROUP BY town.name
        ORDER BY total_publications DESC
        LIMIT 1;     
    """)
    with engine.connect() as conn:
        return conn.execute(sql).scalar_one()


def date_first_and_last_records(engine: Engine) -> Tuple[date,date]:
    """
    Q5 : The date of the first and last records
    Return: tuple of 2 dates
    """
    sql = text("""
        SELECT MIN(act_date) AS first_act, MAX(act_date) AS last_act
        FROM "act";
    """)
    with engine.connect() as conn:
        row = conn.execute(sql).one()
        return row._mapping["first_act"], row._mapping["last_act"]
    



if __name__ == "__main__":
    """
    Run with: uv run python query.py
    """
    from main import get_engine

    engine = get_engine()
    print("Q1 Number of communes per department: ", communes_per_department(engine))
    print("Q2 Number of acts in Luçon: ", acts_in_town(engine))
    print("Q3 Number of marriage contracts before 1855: ", marriage_contracts_before_1855(engine))
    print("Q4 Town with the highest number of marriage publications: ", town_highest_number_marriage_pub(engine))
    print("Q5 Date of the first and last records: ", date_first_and_last_records(engine))