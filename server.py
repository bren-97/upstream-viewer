#!/usr/bin/env python3
import argparse
import json
import os
import re
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse


DEFAULT_CONFIG_DIRS = ["/etc/nginx/sites-available", "/etc/nginx/conf.d"]
RAW_CONFIG_DIRS = os.environ.get("NGINX_CONFIG_DIRS", ",".join(DEFAULT_CONFIG_DIRS))
CONFIG_DIRS = [Path(item.strip()) for item in RAW_CONFIG_DIRS.split(",") if item.strip()]
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))


@dataclass
class UpstreamLink:
    name: str
    servers: List[str]
    source: str


def strip_comments(raw: str) -> str:
    return re.sub(r"#.*$", "", raw, flags=re.MULTILINE)


def find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    for idx in range(open_index, len(text)):
        if text[idx] == "{":
            depth += 1
        elif text[idx] == "}":
            depth -= 1
            if depth == 0:
                return idx
    return -1


def extract_blocks(text: str, block_name: str) -> List[str]:
    blocks = []
    regex = re.compile(rf"\b{re.escape(block_name)}\b\s*\{{")
    pos = 0
    while True:
        match = regex.search(text, pos)
        if not match:
            break
        open_brace_idx = match.end() - 1
        close_brace_idx = find_matching_brace(text, open_brace_idx)
        if close_brace_idx == -1:
            pos = match.end()
            continue
        blocks.append(text[open_brace_idx + 1 : close_brace_idx])
        pos = close_brace_idx + 1
    return blocks


def extract_named_blocks(text: str, block_name: str) -> List[Dict[str, str]]:
    blocks = []
    regex = re.compile(rf"\b{re.escape(block_name)}\b\s+([^\s{{]+)\s*\{{")
    pos = 0
    while True:
        match = regex.search(text, pos)
        if not match:
            break
        name = match.group(1)
        open_brace_idx = match.end() - 1
        close_brace_idx = find_matching_brace(text, open_brace_idx)
        if close_brace_idx == -1:
            pos = match.end()
            continue
        blocks.append({"name": name, "body": text[open_brace_idx + 1 : close_brace_idx]})
        pos = close_brace_idx + 1
    return blocks


def normalize_upstream_name(proxy_pass_value: str) -> str:
    stripped = re.sub(r"^https?://", "", proxy_pass_value)
    first_token = re.split(r"[/$\s]", stripped)[0] if stripped else ""
    return first_token


def extract_server_names(server_body: str) -> List[str]:
    names = []
    for match in re.finditer(r"\bserver_name\s+([^;]+);", server_body):
        chunks = [name.strip() for name in re.split(r"\s+", match.group(1).strip()) if name.strip()]
        names.extend(chunks)
    if not names:
        return ["(без server_name)"]
    return sorted(set(names))


def build_upstream_map(text: str) -> Dict[str, List[str]]:
    result = {}
    for block in extract_named_blocks(text, "upstream"):
        servers = [m.group(1).strip() for m in re.finditer(r"\bserver\s+([^;]+);", block["body"])]
        result[block["name"]] = servers
    return result


def extract_proxy_links(server_body: str, upstream_map: Dict[str, List[str]]) -> List[UpstreamLink]:
    links = []
    for match in re.finditer(r"\bproxy_pass\s+([^;]+);", server_body):
        target = match.group(1).strip()
        upstream_name = normalize_upstream_name(target)
        links.append(
            UpstreamLink(
                name=upstream_name or target,
                servers=upstream_map.get(upstream_name, []),
                source=f"proxy_pass {target}",
            )
        )
    return links


def parse_servers_from_text(raw: str, conf_file: str, upstream_map: Dict[str, List[str]]) -> List[Dict]:
    text = strip_comments(raw)
    sites = []

    for index, server_body in enumerate(extract_blocks(text, "server"), start=1):
        links = extract_proxy_links(server_body, upstream_map)
        seen = set()
        unique_upstreams = []
        for upstream in [link.__dict__ for link in links]:
            key = f"{upstream['name']}||{','.join(upstream['servers'])}||{upstream['source']}"
            if key in seen:
                continue
            seen.add(key)
            unique_upstreams.append(upstream)

        names = extract_server_names(server_body)
        sites.append(
            {
                "host": ", ".join(names),
                "hostNames": names,
                "serverBlocksCount": 1,
                "upstreams": unique_upstreams,
                "confFile": conf_file,
                "serverBlockIndex": index,
            }
        )

    sites.sort(key=lambda item: (item["host"], item["confFile"], item["serverBlockIndex"]))
    return sites


def collect_nginx_files(config_dirs: List[Path]) -> List[Path]:
    files: List[Path] = []
    seen = set()
    for conf_dir in config_dirs:
        if not conf_dir.exists():
            continue
        for conf_file in sorted(conf_dir.glob("*.conf")):
            resolved = conf_file.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(resolved)
    return files


def load_hosts_from_files(config_files: List[Path]) -> List[Dict]:
    file_contents: List[Tuple[Path, str]] = []
    merged_text_chunks: List[str] = []

    for conf_file in config_files:
        try:
            raw = conf_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        file_contents.append((conf_file, raw))
        merged_text_chunks.append(raw)

    merged_text = "\n\n".join(merged_text_chunks)
    upstream_map = build_upstream_map(strip_comments(merged_text))

    hosts: List[Dict] = []
    for conf_file, raw in file_contents:
        hosts.extend(parse_servers_from_text(raw, conf_file.name, upstream_map))
    return hosts


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/hosts":
            self.handle_hosts_api()
            return
        return super().do_GET()

    def handle_hosts_api(self) -> None:
        self.send_json(build_payload(), 200)

    def send_json(self, payload: Dict, status_code: int) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def build_payload() -> Dict:
    config_files = collect_nginx_files(CONFIG_DIRS)
    hosts = load_hosts_from_files(config_files)
    return {
        "hosts": hosts,
        "configDirs": [str(item) for item in CONFIG_DIRS],
        "configFilesCount": len(config_files),
    }


def dump_json_snapshot(target_path: Path) -> None:
    payload = build_payload()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Snapshot written to: {target_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nginx upstream viewer service")
    parser.add_argument("--dump-json", dest="dump_json", help="Write hosts snapshot to JSON and exit")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.dump_json:
        dump_json_snapshot(Path(args.dump_json))
        raise SystemExit(0)

    os.chdir(Path(__file__).resolve().parent)
    print(f"Serving on http://{HOST}:{PORT}")
    print("Reading nginx configs from:")
    for directory in CONFIG_DIRS:
        print(f" - {directory}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
