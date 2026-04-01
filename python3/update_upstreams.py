#!/usr/bin/env python3

import argparse
import io
import json
import os
import re


DEFAULT_CONFIG_DIRS = ["/etc/nginx/conf.d", "/etc/nginx/sites-available"]
DEFAULT_OUTPUT = "/var/www/upstream-viewer/data/hosts.json"
IGNORED_SUFFIXES = ("~", ".bak", ".swp", ".tmp", ".dpkg-old", ".dpkg-dist", ".disabled")


def strip_comments(raw):
    return re.sub(r"#.*$", "", raw, flags=re.MULTILINE)


def find_matching_brace(text, open_index):
    depth = 0
    idx = open_index
    while idx < len(text):
        if text[idx] == "{":
            depth += 1
        elif text[idx] == "}":
            depth -= 1
            if depth == 0:
                return idx
        idx += 1
    return -1


def extract_blocks(text, block_name):
    blocks = []
    regex = re.compile(r"\b%s\b\s*\{" % re.escape(block_name))
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
        blocks.append(text[open_brace_idx + 1:close_brace_idx])
        pos = close_brace_idx + 1
    return blocks


def extract_named_blocks(text, block_name):
    blocks = []
    regex = re.compile(r"\b%s\b\s+([^\s\{]+)\s*\{" % re.escape(block_name))
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
        blocks.append({"name": name, "body": text[open_brace_idx + 1:close_brace_idx]})
        pos = close_brace_idx + 1
    return blocks


def normalize_upstream_name(proxy_pass_value):
    stripped = re.sub(r"^https?://", "", proxy_pass_value)
    parts = re.split(r"[/$\s]", stripped) if stripped else []
    return parts[0] if parts else ""


def extract_server_names(server_body):
    names = []
    for match in re.finditer(r"\bserver_name\s+([^;]+);", server_body):
        chunks = [name.strip() for name in re.split(r"\s+", match.group(1).strip()) if name.strip()]
        names.extend(chunks)
    if not names:
        return ["(без server_name)"]
    return sorted(set(names))


def build_upstream_map(text):
    result = {}
    for block in extract_named_blocks(text, "upstream"):
        servers = [m.group(1).strip() for m in re.finditer(r"\bserver\s+([^;]+);", block["body"])]
        result[block["name"]] = servers
    return result


def extract_proxy_links(server_body, upstream_map):
    links = []
    for match in re.finditer(r"\bproxy_pass\s+([^;]+);", server_body):
        target = match.group(1).strip()
        upstream_name = normalize_upstream_name(target)
        links.append({
            "name": upstream_name or target,
            "servers": upstream_map.get(upstream_name, []),
            "source": "proxy_pass %s" % target
        })
    return links


def parse_servers_from_text(raw, conf_file, upstream_map):
    text = strip_comments(raw)
    sites = []
    index = 1
    for server_body in extract_blocks(text, "server"):
        links = extract_proxy_links(server_body, upstream_map)
        seen = set()
        unique_upstreams = []
        for upstream in links:
            key = "%s||%s||%s" % (
                upstream["name"],
                ",".join(upstream["servers"]),
                upstream["source"]
            )
            if key in seen:
                continue
            seen.add(key)
            unique_upstreams.append(upstream)

        names = extract_server_names(server_body)
        sites.append({
            "host": ", ".join(names),
            "hostNames": names,
            "serverBlocksCount": 1,
            "upstreams": unique_upstreams,
            "confFile": conf_file,
            "serverBlockIndex": index
        })
        index += 1

    sites.sort(key=lambda item: (item["host"], item["confFile"], item["serverBlockIndex"]))
    return sites


def collect_nginx_files(config_dirs):
    files = []
    seen = set()
    for conf_dir in config_dirs:
        if not os.path.isdir(conf_dir):
            continue
        for name in sorted(os.listdir(conf_dir)):
            if name.startswith("."):
                continue
            if name.endswith(IGNORED_SUFFIXES):
                continue
            full = os.path.realpath(os.path.join(conf_dir, name))
            if not os.path.isfile(full):
                continue
            if full in seen:
                continue
            seen.add(full)
            files.append(full)
    return files


def load_hosts_from_files(config_files):
    file_contents = []
    merged_text_chunks = []

    for conf_file in config_files:
        try:
            with io.open(conf_file, "r", encoding="utf-8", errors="ignore") as handle:
                raw = handle.read()
        except IOError:
            continue
        file_contents.append((conf_file, raw))
        merged_text_chunks.append(raw)

    merged_text = "\n\n".join(merged_text_chunks)
    upstream_map = build_upstream_map(strip_comments(merged_text))

    hosts = []
    for conf_file, raw in file_contents:
        hosts.extend(parse_servers_from_text(raw, os.path.basename(conf_file), upstream_map))
    return hosts


def build_payload(config_dirs):
    config_files = collect_nginx_files(config_dirs)
    hosts = load_hosts_from_files(config_files)
    return {
        "hosts": hosts,
        "configDirs": config_dirs,
        "configFilesCount": len(config_files)
    }


def ensure_parent(path):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)


def dump_json_snapshot(target_path, config_dirs):
    payload = build_payload(config_dirs)
    ensure_parent(target_path)
    with io.open(target_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2))
    print("Snapshot written to: %s" % target_path)


def parse_args():
    parser = argparse.ArgumentParser(description="Nginx upstream snapshot generator (Python 3)")
    parser.add_argument(
        "--config-dirs",
        default=",".join(DEFAULT_CONFIG_DIRS),
        help="Comma-separated list of nginx config directories"
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Path to hosts JSON output file"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config_dirs = [item.strip() for item in args.config_dirs.split(",") if item.strip()]
    dump_json_snapshot(args.output, config_dirs)


if __name__ == "__main__":
    main()
