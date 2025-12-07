#!C:/Program Files/Python312/python.exe
"""
save_and_show.py
A simple CGI script that:
 - receives a posted file,
 - saves it under ./uploads (created if needed),
 - then displays the contents back to the client (text shown in <pre>, binary shown as hex/summary).
"""

import cgi
import os
import sys
import html
from pathlib import Path

UPLOAD_DIR = Path.cwd() / "uploads"   # uses current working dir; change as needed
MAX_DISPLAY_BYTES = 200000  # max bytes to attempt to display (avoid huge responses)

def secure_filename(filename: str) -> str:
    # Very small sanitizer: keep basename and replace spaces; for production use a robust lib
    name = os.path.basename(filename)
    return name.replace(" ", "_")

def is_text_bytes(b: bytes) -> bool:
    # naive check: if contains null bytes then binary; else try decode as utf-8
    if b'\x00' in b:
        return False
    try:
        b.decode('utf-8')
        return True
    except Exception:
        return False

def chunked_write(src_file, dest_path):
    with open(dest_path, "wb") as out:
        while True:
            chunk = src_file.read(65536)
            if not chunk:
                break
            out.write(chunk)

def print_headers():
    print("Content-Type: text/html; charset=utf-8")
    print()  # end headers

def main():
    form = cgi.FieldStorage()
    fileitem = form.getfirst("uploaded_file")  # quick check
    # proper FieldStorage access:
    filefield = form["uploaded_file"] if "uploaded_file" in form else None

    print_headers()
    print("<!doctype html><html><head><meta charset='utf-8'><title>Upload result</title></head><body>")
    print("<h2>Upload result</h2>")

    if filefield is None or not getattr(filefield, "filename", None):
        print("<p><strong>No file uploaded.</strong></p>")
        print("</body></html>")
        return

    original_name = filefield.filename
    safe_name = secure_filename(original_name)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = UPLOAD_DIR / safe_name

    try:
        # Save to disk in streaming manner (avoid storing full file in memory)
        chunked_write(filefield.file, saved_path)
    except Exception as e:
        print(f"<p><strong>Error saving file:</strong> {html.escape(str(e))}</p>")
        print("</body></html>")
        return

    size = saved_path.stat().st_size
    print(f"<p>Saved file: <strong>{html.escape(safe_name)}</strong> ({size} bytes) to <code>{html.escape(str(saved_path))}</code></p>")

    # Read a limited amount to display
    try:
        with open(saved_path, "rb") as f:
            sample = f.read(MAX_DISPLAY_BYTES + 1)
    except Exception as e:
        print(f"<p><strong>Can't open saved file:</strong> {html.escape(str(e))}</p>")
        print("</body></html>")
        return

    if len(sample) == 0:
        print("<p><em>File is empty.</em></p>")
    else:
        if is_text_bytes(sample):
            # decode safely and escape HTML
            try:
                text = sample.decode("utf-8")
            except UnicodeDecodeError:
                text = sample.decode("latin-1", errors="replace")
            safe_text = html.escape(text)
            if len(sample) > MAX_DISPLAY_BYTES:
                print(f"<p>File is large — showing first {MAX_DISPLAY_BYTES} bytes:</p>")
            print("<h3>File contents (text)</h3>")
            print("<pre style='white-space: pre-wrap; word-break: break-word; border: 1px solid #ccc; padding: 8px;'>")
            print(safe_text)
            print("</pre>")
        else:
            # Binary file: show a short hex preview and a download link
            show_bytes = sample[:256]
            hex_preview = show_bytes.hex()
            print("<h3>Binary file detected</h3>")
            print("<p>Displaying a small hex preview (first 256 bytes):</p>")
            print("<pre style='background:#f7f7f7; padding:8px; border:1px solid #ddd;'>" + html.escape(hex_preview) + "</pre>")

    # Provide a download link
    # NOTE: This assumes your webserver will serve the uploads directory; if not, you may need to serve the file via a script.
    print(f"<p><a href='/uploads/{html.escape(safe_name)}' download>Download the saved file</a></p>")

    print("</body></html>")

if __name__ == "__main__":
    main()
 