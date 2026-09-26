import os
import shutil
import sys
from pathlib import Path

from office365.runtime.auth.client_credential import ClientCredential
from office365.sharepoint.client_context import ClientContext


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        raise SystemExit(1)
    return value


def safe_join(base: Path, name: str) -> Path:
    """Join name under base; reject path traversal / separators."""
    if not name or name in (".", ".."):
        raise ValueError(f"Rejected empty or relative name: {name!r}")
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError(f"Rejected path traversal or separator in name: {name!r}")
    clean = os.path.basename(name)
    if clean != name or not clean or ".." in clean:
        raise ValueError(f"Rejected unsafe name: {name!r}")
    base_resolved = base.resolve()
    candidate = (base_resolved / clean).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(f"Path escapes base directory: {name!r}") from exc
    return candidate


client_id = require_env("SHAREPOINT_CLIENT_ID")
client_secret = require_env("SHAREPOINT_CLIENT_SECRET")
site_url = require_env("SHAREPOINT_SITE_URL")
library_title = os.environ.get("SHAREPOINT_LIBRARY_TITLE", "YourLibraryTitle")
temp_dir = os.environ.get("SHAREPOINT_TEMP_DIR", "temp_download")
zip_file = os.environ.get("SHAREPOINT_OUTPUT_ZIP", "output.zip")

ctx = ClientContext(site_url).with_credentials(ClientCredential(client_id, client_secret))

library = ctx.web.lists.get_by_title(library_title)
root_folder = library.root_folder
ctx.load(root_folder)
ctx.execute_query()


def download_folder(ctx, folder, local_dir):
    local_base = Path(local_dir)
    os.makedirs(local_base, exist_ok=True)
    files = folder.files.get().execute_query()
    for file in files:
        file_name = file.name
        local_file_path = safe_join(local_base, file_name)
        with open(local_file_path, "wb") as local_file:
            file.download(local_file).execute_query()
            print(f"Downloaded {file_name} to {local_file_path}")
    subfolders = folder.folders.get().execute_query()
    for subfolder in subfolders:
        subfolder_name = subfolder.name
        sub_local_dir = safe_join(local_base, subfolder_name)
        download_folder(ctx, subfolder, str(sub_local_dir))


shutil.rmtree(temp_dir, ignore_errors=True)
download_folder(ctx, root_folder, temp_dir)
base_name = os.path.splitext(zip_file)[0]
shutil.make_archive(base_name, "zip", temp_dir)
print(f"Zip file created at {zip_file}")
