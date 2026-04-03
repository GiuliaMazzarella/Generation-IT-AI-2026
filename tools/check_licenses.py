from __future__ import annotations

import argparse
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILES = [ROOT / 'requirements.txt', ROOT / 'requirements-dev.txt']
ALLOWED_LICENSE_FRAGMENTS = (
    'MIT',
    'BSD',
    'Apache',
    'ISC',
    'MPL',
    'PSF',
    'Python Software Foundation',
)
MANUAL_LICENSE_OVERRIDES = {
    'fastapi': 'MIT (manual review)',
    'uvicorn': 'BSD-3-Clause (manual review)',
    'cryptography': 'Apache-2.0 OR BSD-3-Clause (manual review)',
}


def parse_requirement_names(path: Path) -> list[str]:
    names: list[str] = []
    if not path.exists():
        return names
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.split('#', 1)[0].strip()
        if not line or line.startswith('-'):
            continue
        match = re.match(r'([A-Za-z0-9_.-]+)', line)
        if match:
            names.append(match.group(1))
    return names


def resolve_license(dist_name: str) -> tuple[str, str, str]:
    dist = metadata.distribution(dist_name)
    meta = dist.metadata
    version = dist.version
    license_field = (meta.get('License') or '').strip()
    classifiers = [value for key, value in meta.items() if key == 'Classifier' and 'License' in value]
    combined = ' | '.join(filter(None, [license_field] + classifiers)).strip() or 'UNKNOWN'

    if combined == 'UNKNOWN':
        combined = MANUAL_LICENSE_OVERRIDES.get(dist_name.lower(), combined)

    status = 'OK' if any(fragment.lower() in combined.lower() for fragment in ALLOWED_LICENSE_FRAGMENTS) else 'REVIEW'
    return version, combined, status


def main() -> int:
    parser = argparse.ArgumentParser(description='Check third-party dependency licenses from requirements files.')
    parser.add_argument('--fail-on-unknown', action='store_true', help='Exit with code 1 when any dependency requires manual review.')
    args = parser.parse_args()

    names: list[str] = []
    seen: set[str] = set()
    for req_file in DEFAULT_FILES:
        for name in parse_requirement_names(req_file):
            normalized = name.lower()
            if normalized not in seen:
                names.append(name)
                seen.add(normalized)

    print('Package'.ljust(18), 'Version'.ljust(12), 'Status'.ljust(8), 'License summary')
    print('-' * 88)

    needs_review = False
    for name in names:
        try:
            version, license_text, status = resolve_license(name)
        except metadata.PackageNotFoundError:
            version, license_text, status = '-', 'PACKAGE NOT INSTALLED', 'REVIEW'
        print(name.ljust(18), version.ljust(12), status.ljust(8), license_text)
        if status != 'OK':
            needs_review = True

    if needs_review:
        print('\nResult: one or more dependencies require manual license review.')
        return 1 if args.fail_on_unknown else 0

    print('\nResult: all detected dependencies match the allowed license families.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
