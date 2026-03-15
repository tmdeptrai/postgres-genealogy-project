"""
Parses ../raw_data/mariages_L3.csv into a dict of pd.DataFrame matching
the relational schema: department, town, person, act.

This version is optimized with:
+ Better date format handling
+ Processing the CSV in chunks. (default: 10k lines / chunk)
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

VALID_ACT_TYPES = {
    "Certificat de mariage",
    "Contrat de mariage",
    "Divorce",
    "Mariage",
    "Promesse de mariage - fiançailles",
    "Publication de mariage",
    "Rectification de mariage",
}


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


# ==== NEW: FLEXIBLE DATE FORMAT HANDLING =========


def _parse_date_flexible(date_str: str) -> pd.Timestamp | None:
    """
    Attempts to parse a date string flexibly, handling incomplete dates,
    non-numeric characters, and date ranges.
    """
    if not date_str:
        return None

    original_date_str = date_str

    # Handle date ranges by taking the first year
    if "-" in date_str:
        date_str = date_str.split("-")[0].strip()

    # Clean non-numeric characters from date parts
    parts = date_str.split("/")
    cleaned_parts = []
    for part in parts:
        cleaned_parts.append("".join(filter(str.isdigit, part)))

    date_str = "/".join(cleaned_parts)

    # Handle '00' for day or month
    if len(cleaned_parts) == 3:
        day, month, year = cleaned_parts
        if day == "00":
            day = "01"
        if month == "00":
            month = "01"
        date_str = f"{day}/{month}/{year}"

    # Try common formats first (DD/MM/YYYY, YYYY-MM-DD, etc.)
    parsed_date = pd.to_datetime(date_str, dayfirst=True, errors="coerce")

    # If still NaT, try general inference
    if pd.isna(parsed_date):
        parsed_date = pd.to_datetime(date_str, errors="coerce")

    # If still NaT, try to infer year-only or month-year, assuming default day 1
    if pd.isna(parsed_date):
        try:
            # For 'YYYY' -> '01/01/YYYY'
            if len(date_str) == 4 and date_str.isdigit():
                parsed_date = pd.to_datetime(
                    f"01/01/{date_str}", dayfirst=True, errors="coerce"
                )
            # For 'MM/YYYY'
            elif len(cleaned_parts) == 2:
                month, year = cleaned_parts
                if month == "00":
                    month = "01"
                parsed_date = pd.to_datetime(
                    f"01/{month}/{year}", dayfirst=True, errors="coerce"
                )

        except Exception:
            pass  # Keep parsed_date as NaT if this fails too

    if pd.isna(parsed_date):
        return None
    return parsed_date.date()


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
    chunk_size: int = 10000,
) -> dict[str, pd.DataFrame]:
    """
    Parse the civil registry CSV into normalized DataFrames, processing
    the file in chunks to handle large datasets efficiently.
    """

    dept_set: set = set()
    town_rows: list = []
    town_index: dict = {}
    person_rows: list = []
    person_index: dict = {}
    act_rows: list = []
    skipped = 0
    total_rows = 0

    reader = pd.read_csv(
        csv_path,
        sep=sep,
        encoding=encoding,
        header=None,
        names=CSV_COLUMNS,
        dtype=str,
        chunksize=chunk_size,
    )

    print(f"Starting to process {csv_path} in chunks of {chunk_size}...")

    for chunk in reader:
        total_rows += len(chunk)
        print(f"  Processing rows {total_rows - len(chunk) + 1} to {total_rows}...")
        for _, row in chunk.iterrows():

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
            if act_type not in VALID_ACT_TYPES:
                print(
                    f"  ⚠ Row {row['id']}: unrecognized act_type '{act_type}' — skipped"
                )
                skipped += 1
                continue

            # ── Date (DD/MM/YYYY) ───────────────────────────────────────────────
            date_raw = _clean(row["act_date"])
            act_date = _parse_date_flexible(date_raw)
            if act_date is None and date_raw is not None:
                print(f"  ⚠ Row {row['id']}: unparseable date '{date_raw}'")

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

    print(f"Parsed successfully ({skipped} rows skipped out of {total_rows} total):")
    for name, df in tables.items():
        print(f"  {name:>12}: {len(df):>6} rows")

    return tables


if __name__ == "__main__":
    tables = parse_mariages()
    for name, df in tables.items():
        print(f"=== {name} ===")
        print(df.head(10).to_string(index=False))
