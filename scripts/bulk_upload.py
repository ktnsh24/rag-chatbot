#!/usr/bin/env python3
"""
Bulk Upload Script — Upload multiple files to the RAG Chatbot API.

Usage:
    # Upload all PDFs in a folder:
    python scripts/bulk_upload.py docs/sample-data/*.pdf

    # Upload specific files:
    python scripts/bulk_upload.py file1.pdf file2.txt file3.md

    # Upload to a different server:
    python scripts/bulk_upload.py --url http://localhost:8080 docs/*.pdf

    # Use single-file endpoint (one request per file, slower):
    python scripts/bulk_upload.py --single docs/*.pdf

Supported formats: PDF, TXT, MD, CSV, DOCX
"""

import argparse
import sys
import time
from pathlib import Path

import httpx

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".docx"}
DEFAULT_URL = "http://localhost:8000"


def validate_files(file_paths: list[str]) -> list[Path]:
    """Validate that all files exist and have supported extensions."""
    valid: list[Path] = []
    for fp in file_paths:
        path = Path(fp)
        if not path.exists():
            print(f"  ❌ File not found: {path}")
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"  ❌ Unsupported format: {path.suffix} ({path.name})")
            continue
        valid.append(path)
    return valid


def upload_batch(base_url: str, files: list[Path]) -> None:
    """Upload multiple files in a single batch request."""
    url = f"{base_url}/api/documents/upload-batch"
    print(f"\n📦 Batch uploading {len(files)} files to {url}")
    print("─" * 60)

    # Build multipart form data
    file_tuples = []
    for path in files:
        file_tuples.append(("files", (path.name, path.read_bytes())))

    start = time.time()
    with httpx.Client(timeout=300) as client:
        response = client.post(url, files=file_tuples)
    elapsed = time.time() - start

    if response.status_code != 200:
        print(f"  ❌ HTTP {response.status_code}: {response.text}")
        return

    data = response.json()
    print(f"\n📊 Results ({elapsed:.1f}s):")
    print(f"  Total files:  {data['total_files']}")
    print(f"  Succeeded:    {data['succeeded']}")
    print(f"  Failed:       {data['failed']}")
    print(f"  Total chunks: {data['total_chunks']}")
    print()

    for result in data["results"]:
        status = "✅" if result["status"] == "ready" else "❌"
        print(f"  {status} {result['filename']} — {result['chunk_count']} chunks")
        if result.get("error"):
            print(f"     Error: {result['error']}")

    print(f"\n{data['message']}")


def upload_single(base_url: str, files: list[Path]) -> None:
    """Upload files one by one (fallback for older API versions)."""
    url = f"{base_url}/api/documents/upload"
    print(f"\n📄 Uploading {len(files)} files one-by-one to {url}")
    print("─" * 60)

    total_chunks = 0
    succeeded = 0
    start = time.time()

    with httpx.Client(timeout=120) as client:
        for path in files:
            print(f"\n  📤 {path.name}...", end=" ")
            try:
                response = client.post(
                    url,
                    files={"file": (path.name, path.read_bytes())},
                )
                if response.status_code == 200:
                    data = response.json()
                    chunks = data.get("chunk_count", 0)
                    total_chunks += chunks
                    succeeded += 1
                    print(f"✅ {chunks} chunks")
                else:
                    print(f"❌ HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ {e}")

    elapsed = time.time() - start
    print(f"\n📊 Results ({elapsed:.1f}s): {succeeded}/{len(files)} files, {total_chunks} chunks")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk upload files to the RAG Chatbot API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("files", nargs="+", help="File paths to upload (supports glob)")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"API base URL (default: {DEFAULT_URL})")
    parser.add_argument("--single", action="store_true", help="Upload one-by-one instead of batch")
    args = parser.parse_args()

    print("🔍 Validating files...")
    valid_files = validate_files(args.files)

    if not valid_files:
        print("\n❌ No valid files to upload.")
        sys.exit(1)

    print(f"  ✅ {len(valid_files)} valid files")

    if args.single:
        upload_single(args.url, valid_files)
    else:
        upload_batch(args.url, valid_files)


if __name__ == "__main__":
    main()
