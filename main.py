import os
import argparse
from pathlib import Path
from typing import Dict, Iterable
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

INT32_MIN = -2_147_483_648
INT32_MAX =  2_147_483_647

def get_engine() -> Engine:
    """
    Create and return a SQLAlchemy engine using credentials stored in .env
    """
    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_DIRECT")
    if not url:
        raise RuntimeError("Missing DATABASE_URL (or DATABASE_URL_DIRECT) in .env")
    return create_engine(url, pool_pre_ping=True, poolclass=NullPool)


def _chunks(rows: list[dict], size: int) -> Iterable[list[dict]]:
    """
    Split a list of dictionaries into batches
    """
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _to_records(df: pd.DataFrame) -> list[dict]:
    """
    Convert a pandas DataFrame to a list of dicts for SQLAlchemy executemany() 
    (NA to None)
    """
    return df.where(pd.notna(df), None).to_dict(orient="records")

def _clean_int(series: pd.Series, required: bool) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    # remove infinities
    s = s.replace([np.inf, -np.inf], pd.NA)
    # remove out of range
    s = s.mask((s < INT32_MIN) | (s > INT32_MAX), pd.NA)
    if required:
        return s.astype("Int64")
    return s.astype("Int64")

def normalize_tables(tables: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Prepare DataFrames so they match the database schema constraints
    - act.id is an INTEGER
    - act.act_date is NOT NULL
    - Foreign key columns must be int or NULL
    """
    t = dict(tables)
    act = t["act"].copy()

    # id must be a valid int (PK)
    act["id"] = _clean_int(act["id"], required=True)
    act = act[act["id"].notna()].copy()
    act["id"] = act["id"].astype(int)

    for col in ["a_id", "b_id", "town_id"]:
        act[col] = _clean_int(act[col], required=True)

    act["view_num"] = _clean_int(act["view_num"], required=False)
    act = act[act["act_date"].notna()].copy()
    act = act[act["a_id"].notna() & act["b_id"].notna() & act["town_id"].notna()].copy()

    t["act"] = act
    person = t["person"].copy()

    for col in ["father_id", "mother_id"]:
        if col in person.columns:
            person[col] = _clean_int(person[col],required=True)
    t["person"] = person

    return t


def truncate_all(conn) -> None:
    """
    Remove all data from all tables and restart SERIAL counters
    """
    conn.execute(text('TRUNCATE TABLE "act", "person", "town", "department" RESTART IDENTITY CASCADE;'))


def sync_sequences(conn) -> None:
    """
    Fix SERIAL sequences after inserting explicit IDs
    """
    conn.execute(
        text(
            'SELECT setval(pg_get_serial_sequence(\'"town"\', \'id\'), '
            "COALESCE((SELECT MAX(id) FROM \"town\"), 1), true);"
        )
    )
    conn.execute(
        text(
            'SELECT setval(pg_get_serial_sequence(\'"person"\', \'id\'), '
            "COALESCE((SELECT MAX(id) FROM \"person\"), 1), true);"
        )
    )


def load_tables(
    engine: Engine,
    tables: Dict[str, pd.DataFrame],
    truncate: bool = False,
    chunk_size: int = 5000,
) -> None:
    """
    Load DataFrames into PostgreSQL
    1) department
    2) town        (FK -> department)
    3) person      (self-FK father_id/mother_id)
    4) act         (FK -> person, town)
    """
    tables = normalize_tables(tables)

    df_department = tables["department"]
    df_town = tables["town"]
    df_person = tables["person"]
    df_act = tables["act"]

    with engine.begin() as conn:
        if truncate:
            truncate_all(conn)
        # 1) Load department table
        dept_records = _to_records(df_department[["code"]])
        conn.execute(
            text('INSERT INTO "department" ("code") VALUES (:code) ON CONFLICT ("code") DO NOTHING;'),
            dept_records,
        )

        # 2) Load town table
        # town.dept_code references department.code
        town_records = _to_records(df_town[["id", "name", "dept_code"]])
        for batch in _chunks(town_records, chunk_size):
            conn.execute(
                text(
                    'INSERT INTO "town" ("id","name","dept_code") VALUES (:id,:name,:dept_code) '
                    'ON CONFLICT ("id") DO UPDATE SET '
                    '"name"=EXCLUDED."name", "dept_code"=EXCLUDED."dept_code";'
                ),
                batch,
            )

        # 3) Load person table
        # person.father_id and person.mother_id reference person.id
        # To avoid FK conflicts, we insert all persons first with father_id/mother_id = NULL,
        # then update the parent links afterward once all rows exist
        base_people = df_person[["id", "last_name", "first_name"]].copy()
        base_people["father_id"] = None
        base_people["mother_id"] = None

        people_records = _to_records(base_people[["id", "last_name", "first_name", "father_id", "mother_id"]])
        for batch in _chunks(people_records, chunk_size):
            conn.execute(
                text(
                    'INSERT INTO "person" ("id","last_name","first_name","father_id","mother_id") '
                    'VALUES (:id,:last_name,:first_name,:father_id,:mother_id) '
                    'ON CONFLICT ("id") DO UPDATE SET '
                    '"last_name"=EXCLUDED."last_name", "first_name"=EXCLUDED."first_name";'
                ),
                batch,
            )

        # Update parent links
        parent_links = df_person[["id", "father_id", "mother_id"]].copy()
        parent_records = [
            r for r in _to_records(parent_links)
            if (r["father_id"] is not None or r["mother_id"] is not None)
        ]
        for batch in _chunks(parent_records, chunk_size):
            conn.execute(
                text('UPDATE "person" SET "father_id"=:father_id, "mother_id"=:mother_id WHERE "id"=:id;'),
                batch,
            )

        # 4) Load act table
        # act references:
        # a_id, b_id -> person.id
        # town_id    -> town.id
        # So towns and persons must exist first
        act_records = _to_records(df_act[["id", "act_type", "a_id", "b_id", "town_id", "act_date", "view_num"]])
        for batch in _chunks(act_records, chunk_size):
            conn.execute(
                text(
                    'INSERT INTO "act" ("id","act_type","a_id","b_id","town_id","act_date","view_num") '
                    'VALUES (:id,:act_type,:a_id,:b_id,:town_id,:act_date,:view_num) '
                    'ON CONFLICT ("id") DO UPDATE SET '
                    '"act_type"=EXCLUDED."act_type", "a_id"=EXCLUDED."a_id", "b_id"=EXCLUDED."b_id", '
                    '"town_id"=EXCLUDED."town_id", "act_date"=EXCLUDED."act_date", "view_num"=EXCLUDED."view_num";'
                ),
                batch,
            )

        # Update sequences to avoid conflict for future INSERT
        sync_sequences(conn)


def main():
    """
    Run with uv run python main.py --csv raw_data/mariages_L3_5k.csv --truncate
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="raw_data/mariages_L3_5k.csv", help="Path to the input CSV")
    parser.add_argument("--truncate", action="store_true", help="Clear all tables before loading")
    parser.add_argument("--chunk-size", type=int, default=5000, help="Batch size for INSERT statements")
    args = parser.parse_args()

    from utils.data_parser import parse_mariages

    csv_path = str(Path(args.csv))
    tables = parse_mariages(csv_path=csv_path)
    engine = get_engine()
    load_tables(engine, tables, truncate=args.truncate, chunk_size=args.chunk_size)
    print("Loaded data into PostgreSQL.")


if __name__ == "__main__":
    main()