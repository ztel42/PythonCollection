import datetime
import os
import sys

import pandas as pd
from office365.runtime.auth.client_credential import ClientCredential
from office365.sharepoint.client_context import ClientContext


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        raise SystemExit(1)
    return value


def parse_odata_utc_datetime(value: str) -> str:
    """Validate as UTC ISO datetime and return a known-safe OData string."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Empty datetime")
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        dt = datetime.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO datetime: {value!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


client_id = require_env("SHAREPOINT_CLIENT_ID")
client_secret = require_env("SHAREPOINT_CLIENT_SECRET")
site_url = require_env("SHAREPOINT_SITE_URL")
list_title = os.environ.get("SHAREPOINT_LIST_TITLE", "YourListTitle")
excel_file = os.environ.get("SHAREPOINT_OUTPUT_XLSX", "output.xlsx")
last_checked_file = os.environ.get("SHAREPOINT_LAST_CHECKED_FILE", "last_checked.txt")

try:
    with open(last_checked_file, "r", encoding="utf-8") as f:
        raw_last_checked = f.read().strip()
except FileNotFoundError:
    raw_last_checked = "1900-01-01T00:00:00Z"

try:
    last_checked_time = parse_odata_utc_datetime(raw_last_checked)
except ValueError as exc:
    print(f"Invalid last_checked_time in {last_checked_file}: {exc}", file=sys.stderr)
    raise SystemExit(1)

ctx = ClientContext(site_url).with_credentials(ClientCredential(client_id, client_secret))

sp_list = ctx.web.lists.get_by_title(list_title)

fields = sp_list.fields.get().execute_query()
field_names = [field.internal_name for field in fields]

query = f"Created gt datetime'{last_checked_time}'"
l_items = sp_list.get_items().filter(query)
ctx.load(l_items)
ctx.execute_query()

data = []
for item in l_items:
    row = {field: item.properties.get(field, None) for field in field_names}
    data.append(row)

new_df = pd.DataFrame(data)

try:
    existing_df = pd.read_excel(excel_file)
except FileNotFoundError:
    existing_df = pd.DataFrame()

combined_df = pd.concat([existing_df, new_df], ignore_index=True)
combined_df.to_excel(excel_file, index=False)

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(last_checked_file, "w", encoding="utf-8") as f:
    f.write(now)
