#!/usr/bin/env python3
"""
Generate a systems_map.json describing GitHub repositories listed in repos.txt.

Inputs:
  - repos.txt (sibling to this script): one "owner/repo" per line

Auth:
  - Set GITHUB_TOKEN in solutions-architect/.env (preferred)
    or export it in the shell environment.

What it collects (best-effort):
  - Repo metadata: description, homepage, topics, default_branch, archived, etc.
  - Language breakdown
  - Contents of common "system mapping" files if present:
      README.md, README.rst, README.txt,
      CODEOWNERS,
      catalog-info.yaml (Backstage),
      openapi.yaml/openapi.yml/swagger.yaml/swagger.yml
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List


GITHUB_GRAPHQL_API = "https://api.github.com/graphql"
API_VERSION = "2022-11-28"


@dataclass
class RepoSpec:
    owner: str
    repo: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD")


def make_evidence(path: Optional[str], text: Optional[str], needle: str, radius: int = 120) -> Dict[str, Optional[str]]:
    snippet: Optional[str] = None
    if isinstance(text, str) and needle:
        idx = text.lower().find(needle.lower())
        if idx >= 0:
            start = max(0, idx - radius)
            end = min(len(text), idx + len(needle) + radius)
            snippet = text[start:end].strip()
    return {
        "path": path,
        "snippet": snippet,
    }


def repo_kind_for(spec: RepoSpec, language: Optional[str], readme_text: Optional[str]) -> str:
    repo_name = spec.repo.lower()
    if "test" in repo_name:
        return "tests"
    if "infra" in repo_name:
        return "infra"
    if "middleware" in repo_name or "sdk" in repo_name:
        return "library"
    if "service" in repo_name:
        return "service"

    readme = (readme_text or "").lower()
    if "microservice" in readme or "service" in readme:
        return "service"
    if "library" in readme or "middleware" in readme:
        return "library"
    if language and language.lower() in {"go", "typescript", "javascript", "python"}:
        return "service"
    return "unknown"


def extract_env_vars(readme_path: Optional[str], readme_text: Optional[str]) -> List[Dict[str, Any]]:
    if not isinstance(readme_text, str) or not readme_text.strip():
        return []

    matches = set(re.findall(r"\b[A-Z][A-Z0-9_]*\b", readme_text))
    keep: List[str] = []
    for name in matches:
        if (
            name == "PORT"
            or name.endswith("_SERVICE_URL")
            or name.endswith("_URL")
            or name.endswith("_TOKEN")
        ):
            keep.append(name)

    out: List[Dict[str, Any]] = []
    for name in sorted(set(keep)):
        out.append(
            {
                "name": name,
                "confidence": "medium",
                "evidence": make_evidence(readme_path, readme_text, name),
            }
        )
    return out


def infer_depends_on(
    spec: RepoSpec,
    env_vars: List[Dict[str, Any]],
    readme_path: Optional[str],
    readme_text: Optional[str],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for env in env_vars:
        name = env.get("name")
        if not isinstance(name, str) or not name.endswith("_SERVICE_URL"):
            continue
        target = name[: -len("_SERVICE_URL")].lower().replace("_", "-") + "-service"
        key = (spec.repo, target)
        if key in seen or target == spec.repo:
            continue
        seen.add(key)
        out.append(
            {
                "target": target,
                "type": "http",
                "confidence": "medium",
                "evidence": make_evidence(readme_path, readme_text, name),
            }
        )
    return out


def extract_auth_signals(readme_path: Optional[str], readme_text: Optional[str]) -> List[Dict[str, Any]]:
    if not isinstance(readme_text, str) or not readme_text.strip():
        return []
    markers = [
        "AuthGuard",
        "RequireRolesGuard",
        "RequireAllRolesGuard",
        "@Roles",
        "@RequireAllRoles",
        "AuthMiddleware",
        "RequireRoles(",
        "RequireAllRoles(",
    ]
    out: List[Dict[str, Any]] = []
    for marker in markers:
        if marker.lower() in readme_text.lower():
            out.append(
                {
                    "signal": marker,
                    "confidence": "medium",
                    "evidence": make_evidence(readme_path, readme_text, marker),
                }
            )
    return out


def extract_endpoints(
    readme_path: Optional[str],
    readme_text: Optional[str],
    openapi_path: Optional[str],
    openapi_text: Optional[str],
) -> List[Dict[str, Any]]:
    endpoints: List[Dict[str, Any]] = []
    seen = set()

    if isinstance(openapi_text, str) and openapi_text.strip():
        for m in re.finditer(r"(?m)^\s{0,4}(/[^\s:#]+):\s*$", openapi_text):
            path = m.group(1).strip()
            if not path.startswith("/"):
                continue
            key = ("ANY", path)
            if key in seen:
                continue
            seen.add(key)
            endpoints.append(
                {
                    "method": "ANY",
                    "path": path,
                    "source": "openapi",
                    "confidence": "high",
                    "evidence": make_evidence(openapi_path, openapi_text, path),
                }
            )

    if isinstance(readme_text, str) and readme_text.strip():
        method_pattern = r"\b(" + "|".join(HTTP_METHODS) + r")\b\s+`?(/[-A-Za-z0-9_{}:./]+)`?"
        for m in re.finditer(method_pattern, readme_text):
            method = m.group(1).upper()
            path = m.group(2)
            key = (method, path)
            if key in seen:
                continue
            seen.add(key)
            endpoints.append(
                {
                    "method": method,
                    "path": path,
                    "source": "readme",
                    "confidence": "medium",
                    "evidence": make_evidence(readme_path, readme_text, f"{method} {path}"),
                }
            )

    return endpoints


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def load_dotenv(path: Path) -> None:
    """Best-effort .env loader so local tokens work without shell export."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        os.environ[key] = value


def load_repo_list(path: Path) -> List[RepoSpec]:
    if not path.exists():
        die(f"Missing {path.name} beside the script at: {path}")

    specs: List[RepoSpec] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "/" not in line:
            print(f"Skipping invalid line (expected owner/repo): {line}", file=sys.stderr)
            continue
        owner, repo = line.split("/", 1)
        owner, repo = owner.strip(), repo.strip()
        if owner and repo:
            specs.append(RepoSpec(owner=owner, repo=repo))
        else:
            print(f"Skipping invalid line (blank owner or repo): {line}", file=sys.stderr)
    return specs


def github_session() -> Dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "systems-map-generator/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def handle_rate_limit(status_code: int, headers: Dict[str, Any]) -> None:
    # Conservative: if rate-limited, sleep until reset.
    if status_code != 403:
        return
    remaining = headers.get("X-RateLimit-Remaining")
    reset = headers.get("X-RateLimit-Reset")
    if remaining == "0" and reset:
        try:
            reset_ts = int(reset)
            now = int(time.time())
            sleep_s = max(1, reset_ts - now + 1)
            print(f"Rate limit hit. Sleeping {sleep_s}s until reset...", file=sys.stderr)
            time.sleep(sleep_s)
        except ValueError:
            pass


def gh_post_json(s: Dict[str, str], url: str, body: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    raw_body = json.dumps(body).encode("utf-8")

    for attempt in range(3):
        req = urllib.request.Request(
            url,
            data=raw_body,
            headers={**s, "Content-Type": "application/json"},
            method="POST",
        )

        status_code = 0
        headers: Dict[str, Any] = {}
        raw: bytes = b""

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                status_code = getattr(resp, "status", 200)
                headers = dict(resp.headers.items())
                raw = resp.read()
        except urllib.error.HTTPError as e:
            status_code = e.code
            headers = dict((e.headers or {}).items())
            try:
                raw = e.read()
            except Exception:
                raw = b""
        except urllib.error.URLError:
            if attempt < 2:
                time.sleep(1 + attempt)
                continue
            return None, "network_error"

        if status_code == 403:
            handle_rate_limit(status_code, headers)
            if headers.get("X-RateLimit-Remaining") == "0":
                continue

        if status_code in (200, 201):
            try:
                return json.loads(raw.decode("utf-8", errors="replace")), None
            except json.JSONDecodeError:
                return None, "invalid_json"
        if status_code == 404:
            return None, "not_found"
        if status_code == 401:
            return None, "unauthorized"
        if status_code == 403:
            return None, "forbidden"
        if status_code >= 500 and attempt < 2:
            time.sleep(1 + attempt)
            continue
        return None, f"http_{status_code}"

    return None, "failed"


def _gql_quote(value: str) -> str:
    return json.dumps(value)


def build_repo_query_block(alias: str, spec: RepoSpec) -> str:
    file_aliases = {
        "readme_md": "README.md",
        "readme_rst": "README.rst",
        "readme_txt": "README.txt",
        "codeowners_root": "CODEOWNERS",
        "codeowners_gh": ".github/CODEOWNERS",
        "catalog_yaml": "catalog-info.yaml",
        "catalog_yml": "catalog-info.yml",
        "openapi_yaml": "openapi.yaml",
        "openapi_yml": "openapi.yml",
        "swagger_yaml": "swagger.yaml",
        "swagger_yml": "swagger.yml",
        "api_openapi_yaml": "api/openapi.yaml",
        "api_openapi_yml": "api/openapi.yml",
        "api_swagger_yaml": "api/swagger.yaml",
        "api_swagger_yml": "api/swagger.yml",
    }

    object_fields = "\n".join(
        f'{a}: object(expression: {_gql_quote(f"HEAD:{p}")}) {{ ... on Blob {{ text }} }}'
        for a, p in file_aliases.items()
    )

    return f'''
    {alias}: repository(owner: {_gql_quote(spec.owner)}, name: {_gql_quote(spec.repo)}) {{
      nameWithOwner
      url
      description
      homepageUrl
      visibility
      isPrivate
      isArchived
      isDisabled
      isFork
      defaultBranchRef {{ name }}
      createdAt
      updatedAt
      pushedAt
      licenseInfo {{ spdxId }}
      issues(states: OPEN) {{ totalCount }}
      stargazerCount
      watchers {{ totalCount }}
      forkCount
      primaryLanguage {{ name }}
      owner {{ login __typename }}
      repositoryTopics(first: 100) {{ nodes {{ topic {{ name }} }} }}
      languages(first: 25, orderBy: {{ field: SIZE, direction: DESC }}) {{
        edges {{
          size
          node {{ name }}
        }}
      }}
      {object_fields}
    }}
    '''


def extract_blob_text(repo_node: Dict[str, Any], alias: str) -> Optional[str]:
    node = repo_node.get(alias)
    if not isinstance(node, dict):
        return None
    text = node.get("text")
    return text if isinstance(text, str) else None


def get_repo_bundle_graphql(s: Dict[str, str], specs: List[RepoSpec]) -> Dict[str, Dict[str, Any]]:
    aliases = {f"r{i}": spec for i, spec in enumerate(specs)}
    query = "query BatchRepos {\n" + "\n".join(build_repo_query_block(alias, spec) for alias, spec in aliases.items()) + "\n}"

    payload, err = gh_post_json(s, GITHUB_GRAPHQL_API, {"query": query})
    out: Dict[str, Dict[str, Any]] = {}

    if err or not isinstance(payload, dict):
        for spec in specs:
            out[spec.full_name] = {"full_name": spec.full_name, "error": err or "unknown"}
        return out

    errors_by_alias: Dict[str, str] = {}
    for e in payload.get("errors", []) or []:
        if not isinstance(e, dict):
            continue
        path = e.get("path")
        msg = e.get("message")
        if isinstance(path, list) and path:
            alias = str(path[0])
            errors_by_alias[alias] = str(msg or "graphql_error")

    data = payload.get("data") or {}
    for alias, spec in aliases.items():
        if alias in errors_by_alias:
            out[spec.full_name] = {"full_name": spec.full_name, "error": errors_by_alias[alias]}
            continue

        repo_node = data.get(alias)
        if not isinstance(repo_node, dict):
            out[spec.full_name] = {"full_name": spec.full_name, "error": "not_found"}
            continue

        topics = [
            (((n or {}).get("topic") or {}).get("name"))
            for n in ((repo_node.get("repositoryTopics") or {}).get("nodes") or [])
            if isinstance(n, dict)
        ]
        topics = [t for t in topics if isinstance(t, str)]

        languages: Dict[str, int] = {}
        for edge in ((repo_node.get("languages") or {}).get("edges") or []):
            if not isinstance(edge, dict):
                continue
            lang_name = ((edge.get("node") or {}).get("name"))
            lang_size = edge.get("size")
            if isinstance(lang_name, str) and isinstance(lang_size, int):
                languages[lang_name] = int(lang_size)

        readme_candidates = [
            ("README.md", extract_blob_text(repo_node, "readme_md")),
            ("README.rst", extract_blob_text(repo_node, "readme_rst")),
            ("README.txt", extract_blob_text(repo_node, "readme_txt")),
        ]
        codeowners_candidates = [
            ("CODEOWNERS", extract_blob_text(repo_node, "codeowners_root")),
            (".github/CODEOWNERS", extract_blob_text(repo_node, "codeowners_gh")),
        ]
        catalog_candidates = [
            ("catalog-info.yaml", extract_blob_text(repo_node, "catalog_yaml")),
            ("catalog-info.yml", extract_blob_text(repo_node, "catalog_yml")),
        ]
        openapi_candidates = [
            ("openapi.yaml", extract_blob_text(repo_node, "openapi_yaml")),
            ("openapi.yml", extract_blob_text(repo_node, "openapi_yml")),
            ("swagger.yaml", extract_blob_text(repo_node, "swagger_yaml")),
            ("swagger.yml", extract_blob_text(repo_node, "swagger_yml")),
            ("api/openapi.yaml", extract_blob_text(repo_node, "api_openapi_yaml")),
            ("api/openapi.yml", extract_blob_text(repo_node, "api_openapi_yml")),
            ("api/swagger.yaml", extract_blob_text(repo_node, "api_swagger_yaml")),
            ("api/swagger.yml", extract_blob_text(repo_node, "api_swagger_yml")),
        ]

        def first_present(candidates: List[Tuple[str, Optional[str]]]) -> Tuple[Optional[str], Optional[str]]:
            for p, txt in candidates:
                if isinstance(txt, str):
                    return p, txt
            return None, None

        readme_path, readme_text = first_present(readme_candidates)
        codeowners_path, codeowners_text = first_present(codeowners_candidates)
        catalog_path, catalog_text = first_present(catalog_candidates)
        openapi_path, openapi_text = first_present(openapi_candidates)

        env_vars = extract_env_vars(readme_path, readme_text)
        depends_on = infer_depends_on(spec, env_vars, readme_path, readme_text)
        auth_signals = extract_auth_signals(readme_path, readme_text)
        endpoints = extract_endpoints(readme_path, readme_text, openapi_path, openapi_text)
        repo_kind = repo_kind_for(spec, ((repo_node.get("primaryLanguage") or {}).get("name")), readme_text)

        entry: Dict[str, Any] = {
            "full_name": repo_node.get("nameWithOwner", spec.full_name),
            "html_url": repo_node.get("url"),
            "description": repo_node.get("description"),
            "homepage": repo_node.get("homepageUrl"),
            "topics": topics,
            "visibility": str(repo_node.get("visibility", "")).lower() if repo_node.get("visibility") else None,
            "private": repo_node.get("isPrivate"),
            "archived": repo_node.get("isArchived"),
            "disabled": repo_node.get("isDisabled"),
            "fork": repo_node.get("isFork"),
            "default_branch": ((repo_node.get("defaultBranchRef") or {}).get("name")),
            "created_at": repo_node.get("createdAt"),
            "updated_at": repo_node.get("updatedAt"),
            "pushed_at": repo_node.get("pushedAt"),
            "license": ((repo_node.get("licenseInfo") or {}).get("spdxId")),
            "open_issues_count": ((repo_node.get("issues") or {}).get("totalCount")),
            "stargazers_count": repo_node.get("stargazerCount"),
            "watchers_count": ((repo_node.get("watchers") or {}).get("totalCount")),
            "forks_count": repo_node.get("forkCount"),
            "language": ((repo_node.get("primaryLanguage") or {}).get("name")),
            "owner": {
                "login": ((repo_node.get("owner") or {}).get("login")),
                "type": ((repo_node.get("owner") or {}).get("__typename")),
            },
            "languages_bytes": languages,
            "files": {
                "readme": {"path": readme_path, "text": readme_text} if readme_text else None,
                "codeowners": {"path": codeowners_path, "text": codeowners_text} if codeowners_text else None,
                "catalog": {"path": catalog_path, "text": catalog_text} if catalog_text else None,
                "openapi": {"path": openapi_path, "text": openapi_text} if openapi_text else None,
            },
            "derived": {
                "repo_kind": repo_kind,
                "env_vars": env_vars,
                "auth_signals": auth_signals,
                "endpoints": endpoints,
                "depends_on": depends_on,
            },
        }

        for _, v in list(entry["files"].items()):
            if not v:
                continue
            txt = v.get("text") or ""
            if len(txt) > 200_000:
                v["text"] = txt[:200_000] + "\n\n[TRUNCATED]\n"
                v["truncated"] = True

        out[spec.full_name] = entry

    return out


def main() -> None:
    here = Path(__file__).resolve().parent
    load_dotenv(here / ".env")
    repo_list_path = here / "repos.txt"
    specs = load_repo_list(repo_list_path)
    if not specs:
        die("No valid repos found in repos.txt")

    s = github_session()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        die(
            "GITHUB_TOKEN is required. Add it to solutions-architect/.env as GITHUB_TOKEN=... "
            "to use the GitHub GraphQL API and avoid strict unauthenticated rate limits."
        )

    result: Dict[str, Any] = {
        "schema_version": "1.1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "GitHub GraphQL API",
        "repos": [],
        "dependency_edges": [],
    }

    batch_size = int(os.environ.get("GITHUB_GRAPHQL_BATCH_SIZE", "20"))
    for i in range(0, len(specs), batch_size):
        chunk = specs[i : i + batch_size]
        print(
            "Processing (GraphQL batch): " + ", ".join(s.full_name for s in chunk),
            file=sys.stderr,
        )
        by_repo = get_repo_bundle_graphql(s, chunk)
        for spec in chunk:
            entry = by_repo.get(spec.full_name, {"full_name": spec.full_name, "error": "unknown"})
            result["repos"].append(entry)

            depends_on = (((entry.get("derived") or {}).get("depends_on")) or []) if isinstance(entry, dict) else []
            for dep in depends_on:
                target = dep.get("target") if isinstance(dep, dict) else None
                if not isinstance(target, str) or not target:
                    continue
                result["dependency_edges"].append(
                    {
                        "from": spec.repo,
                        "to": target,
                        "type": dep.get("type", "http") if isinstance(dep, dict) else "http",
                        "confidence": dep.get("confidence", "medium") if isinstance(dep, dict) else "medium",
                        "evidence": dep.get("evidence") if isinstance(dep, dict) else None,
                    }
                )

    out_path = here / "systems_map.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("Interrupted", 130)