"""
Parses ../raw_data/mariages_L3.csv into a dict of pd.DataFrame matching
the relational schema: department, town, person, act.

CSV column layout (no header row):
  0  id
  1  act_type
  2  a_last
  3  a_first
  4  a_father_first          ← father: first name only (no last name)
  5  a_mother_last           ← mother: last name
  6  a_mother_first          ← mother: first name
  7  b_last
  8  b_first
  9  b_father_first          ← father: first name only
  10 b_mother_last           ← mother: last name
  11 b_mother_first          ← mother: first name
  12 town_name
  13 dept_code
  14 act_date  (DD/MM/YYYY)
  15 view_num  (e.g. "48/210" → stored as first integer: 48)

USAGE
-----
    from parse_mariages import parse_mariages
    tables = parse_mariages()
    # returns {"department", "town", "person", "act"} → pd.DataFrame
"""

import pandas as pd

CSV_COLUMNS = [
    "id",
    "act_type",
    "a_last",
    "a_first",
    "a_father_first",
    "a_mother_last",
    "a_mother_first",
    "b_last",
    "b_first",
    "b_father_first",
    "b_mother_last",
    "b_mother_first",
    "town_name",
    "dept_code",
    "act_date",
    "view_num",
]

VALID_DEPT_CODES = {"44", "49", "79", "85"}


def _clean(val) -> str | None:
    """
    Normalize a raw CSV cell value.

    Returns the stripped string value, or None if the value is
    missing (NaN), empty, or the placeholder 'n/a'.
    """
    if pd.isna(val):
        return None
    s = str(val).strip()
    return None if s.lower() in ("n/a", "", "nan") else s


def _get_or_create_person(
    last,
    first,
    father_id,
    mother_id,
    person_rows: list,
    person_index: dict,
) -> int | None:
    """
    Return the id of a matching person, inserting a new row if none exists.

    Deduplication key is (last_name, first_name, father_id, mother_id),
    all uppercased. This means two people are considered the same only if
    their full name AND both parent references match.

    Note: fathers are stored with an empty last_name (data only provides
    their first name), making their dedup key weak — two unrelated fathers
    named 'Jean' with no parent refs will incorrectly collapse into one row.

    Returns None without inserting anything if both last and first are None,
    which represents an unknown person (n/a). This is expected for optional
    parent fields, but would be a data quality issue for person A or B.
    """
    if not last and not first:
        return None
    key = (
        (last or "").upper(),
        (first or "").upper(),
        father_id,
        mother_id,
    )
    if key in person_index:
        return person_index[key]
    new_id = len(person_rows) + 1
    person_rows.append(
        {
            "id": new_id,
            "last_name": last or "",
            "first_name": first or "",
            "father_id": father_id,
            "mother_id": mother_id,
        }
    )
    person_index[key] = new_id
    return new_id


def _get_or_create_town(name, dept_code, town_rows, town_index) -> int:
    """
    Return the id of a matching town, inserting a new row if none exists.

    Deduplication key is (name.upper(), dept_code), since the same town
    name can theoretically exist in different departments.
    """
    key = ((name or "").upper(), dept_code)
    if key in town_index:
        return town_index[key]
    new_id = len(town_rows) + 1
    town_rows.append({"id": new_id, "name": name or "", "dept_code": dept_code})
    town_index[key] = new_id
    return new_id


def parse_mariages(
    csv_path: str = "../raw_data/mariages_L3_5k.csv",
    sep: str = ",",
    encoding: str = "utf-8",
    chunk_size = None,
) -> dict[str, pd.DataFrame]:
    """
    Parse the civil registry CSV(No header row is expected.)
    into normalized DataFrames.

    Reads the raw flat file and splits it into four tables mirroring
    the target relational schema in ../design/normalisation.pdf.

    Entities (persons, towns, departments) are deduplicated in-memory
    using dict indexes keyed on their natural identifiers; surrogate
    integer ids are assigned incrementally.

    Rows (acts) are skipped entirely if dept_code is not one of the four
    valid values ('44', '49', '79', '85'), since a missing department
    makes it impossible to resolve the town foreign key.

    Parent persons with all-null names (unknown in the source data) are
    not inserted; the corresponding father_id / mother_id on the child
    row is left as NULL (pd.NA).

    view_num is stored as the first integer of the raw "folio/total" string
    (e.g. "48/210" → 48), matching the INTEGER type in the schema.

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys: 'department', 'town', 'person', 'act'.
        FK columns (father_id, mother_id, view_num) use pandas
        nullable Int64 to avoid silent casting to float.
    """
    raw = pd.read_csv(
        csv_path,
        sep=sep,
        encoding=encoding,
        header=None,
        names=CSV_COLUMNS,
        dtype=str,
    )
    print(f"Loaded {len(raw)} rows from {csv_path}")

    dept_set: set = set()
    town_rows: list = []
    town_index: dict = {}
    person_rows: list = []
    person_index: dict = {}
    act_rows: list = []
    skipped = 0

    for _, row in raw.iterrows():

        # ── Department ──────────────────────────────────────────────────────
        dept_code = _clean(row["dept_code"])
        if dept_code not in VALID_DEPT_CODES:
            print(f"  ⚠ Row {row['id']}: unknown dept_code '{dept_code}' — skipped")
            skipped += 1
            continue
        dept_set.add(dept_code)

        # ── Town ────────────────────────────────────────────────────────────
        town_id = _get_or_create_town(
            _clean(row["town_name"]), dept_code, town_rows, town_index
        )

        # ── Father of A (first name only, no last name) ─────────────────────
        fa_id = _get_or_create_person(
            None,
            _clean(row["a_father_first"]),
            None,
            None,
            person_rows,
            person_index,
        )
        # ── Mother of A (last + first name) ────────────────────────────────
        ma_id = _get_or_create_person(
            _clean(row["a_mother_last"]),
            _clean(row["a_mother_first"]),
            None,
            None,
            person_rows,
            person_index,
        )
        # ── Person A ────────────────────────────────────────────────────────
        a_id = _get_or_create_person(
            _clean(row["a_last"]),
            _clean(row["a_first"]),
            fa_id,
            ma_id,
            person_rows,
            person_index,
        )

        # ── Father of B ─────────────────────────────────────────────────────
        fb_id = _get_or_create_person(
            None,
            _clean(row["b_father_first"]),
            None,
            None,
            person_rows,
            person_index,
        )
        # ── Mother of B ─────────────────────────────────────────────────────
        mb_id = _get_or_create_person(
            _clean(row["b_mother_last"]),
            _clean(row["b_mother_first"]),
            None,
            None,
            person_rows,
            person_index,
        )
        # ── Person B ────────────────────────────────────────────────────────
        b_id = _get_or_create_person(
            _clean(row["b_last"]),
            _clean(row["b_first"]),
            fb_id,
            mb_id,
            person_rows,
            person_index,
        )

        # ── Act type ────────────────────────────────────────────────────────
        act_type = _clean(row["act_type"]) or ""

        # ── Date (DD/MM/YYYY) ───────────────────────────────────────────────
        date_raw = _clean(row["act_date"])
        try:
            act_date = pd.to_datetime(date_raw, dayfirst=True).date()
        except Exception:
            print(f"  ⚠ Row {row['id']}: unparseable date '{date_raw}'")
            act_date = None

        # ── view_num: "48/210" → store folio number (48) ───────────────────
        view_num = None
        view_raw = _clean(row["view_num"])
        if view_raw:
            try:
                view_num = int(view_raw.split("/")[0])
            except ValueError:
                pass

        act_rows.append(
            {
                "id": _clean(row["id"]),
                "act_type": act_type,
                "a_id": a_id,
                "b_id": b_id,
                "town_id": town_id,
                "act_date": act_date,
                "view_num": view_num,
            }
        )

    # ── Assemble DataFrames ─────────────────────────────────────────────────
    df_dept = pd.DataFrame(sorted(dept_set), columns=["code"])

    df_town = pd.DataFrame(town_rows)[["id", "name", "dept_code"]]

    df_person = pd.DataFrame(person_rows)[
        ["id", "last_name", "first_name", "father_id", "mother_id"]
    ]
    df_person["father_id"] = pd.array(df_person["father_id"], dtype="Int64")
    df_person["mother_id"] = pd.array(df_person["mother_id"], dtype="Int64")

    df_act = pd.DataFrame(act_rows)[
        ["id", "act_type", "a_id", "b_id", "town_id", "act_date", "view_num"]
    ]
    df_act["view_num"] = pd.array(df_act["view_num"], dtype="Int64")

    tables = {
        "department": df_dept,
        "town": df_town,
        "person": df_person,
        "act": df_act,
    }

    print(f"\nParsed successfully ({skipped} rows skipped):")
    for name, df in tables.items():
        print(f"  {name:>12}: {len(df):>6} rows")

    return tables


if __name__ == "__main__":
    tables = parse_mariages()
    for name, df in tables.items():
        print(f"\n=== {name} ===")
        print(df.head(10).to_string(index=False))
