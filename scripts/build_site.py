"""Bundle the static site as a self-contained Cloudflare Worker."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "server" / "index.js"
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/data/notices.json": ("data/notices.json", "application/json; charset=utf-8"),
    "/data/schools.json": ("data/schools.json", "application/json; charset=utf-8"),
}


def main():
    payload = {}
    for route, (relative_path, content_type) in FILES.items():
        payload[route] = {
            "body": (ROOT / relative_path).read_text(encoding="utf-8"),
            "contentType": content_type,
        }

    worker = f"""const files = {json.dumps(payload, ensure_ascii=False)};

export default {{
  async fetch(request) {{
    const url = new URL(request.url);
    const file = files[url.pathname];
    if (!file) {{
      return new Response("Not found", {{ status: 404 }});
    }}
    const isData = url.pathname.startsWith("/data/");
    return new Response(file.body, {{
      headers: {{
        "content-type": file.contentType,
        "cache-control": isData ? "no-cache" : "public, max-age=300",
        "x-content-type-options": "nosniff",
        "referrer-policy": "strict-origin-when-cross-origin"
      }}
    }});
  }}
}};
"""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(worker, encoding="utf-8", newline="\n")
    print(f"Built {OUTPUT.relative_to(ROOT)} with {len(FILES)} routes")


if __name__ == "__main__":
    main()
