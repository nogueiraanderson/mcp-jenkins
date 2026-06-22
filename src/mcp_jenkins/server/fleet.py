"""Fleet-level tools: read across all configured masters at once.

These differ from the per-master tools: they iterate the server-held fleet config
(masters + read-only tokens) rather than a single connected master, so an agent can
discover the fleet and compare it without the user supplying any credentials.
"""

from loguru import logger

from mcp_jenkins.core.fleet import client_for, get_fleet
from mcp_jenkins.server import mcp


@mcp.tool(tags={'read'})
async def list_masters() -> list[dict]:
    """List the active Jenkins masters this server can reach, with a liveness check.

    Returns:
        One entry per configured master: name, url, reachable (bool), version (Jenkins core
        version when reachable), and error (a short message when the liveness check failed).
    """
    results = []
    for master in get_fleet().masters:
        entry: dict = {'name': master.name, 'url': master.url, 'reachable': False, 'version': None}
        try:
            entry['version'] = client_for(master.name).get_version()
            entry['reachable'] = True
        except Exception as e:  # noqa: BLE001
            entry['error'] = str(e)
            logger.warning(f'list_masters: {master.name} liveness failed: {e}')
        results.append(entry)
    return results


@mcp.tool(tags={'read'})
async def list_fleet_plugins(short_name: str | None = None, full: bool = False) -> dict:  # noqa: FBT001, FBT002
    """List installed plugins and their versions across the fleet.

    Args:
        short_name: If given, report only this plugin's version on each master (a drift check,
            e.g. confirming a plugin is uniform fleet-wide).
        full: If True and short_name is None, include the full per-master plugin map. Default
            False returns a compact summary plus a version-drift report.

    Returns:
        With short_name: {"plugin": name, "versions": {master: version|None}, "errors": {...}}.
        Without: {"masters": {master: {"count": N, "core": version}}, "drift": {shortName:
        {master: version}}, "errors": {...}} where drift lists plugins whose version is not
        uniform across the masters that have them installed.
    """
    per_master: dict[str, dict[str, str]] = {}
    core: dict[str, str] = {}
    errors: dict[str, str] = {}

    for master in get_fleet().masters:
        try:
            client = client_for(master.name)
            core[master.name] = client.get_version()
            plugins = client.get_plugins(depth=0)
            per_master[master.name] = {p['shortName']: p.get('version') for p in plugins if p.get('shortName')}
        except Exception as e:  # noqa: BLE001
            errors[master.name] = str(e)
            logger.warning(f'list_fleet_plugins: {master.name} failed: {e}')

    if short_name:
        return {
            'plugin': short_name,
            'versions': {m: vers.get(short_name) for m, vers in per_master.items()},
            'errors': errors,
        }

    all_names = set().union(*(set(v) for v in per_master.values())) if per_master else set()
    drift: dict[str, dict[str, str]] = {}
    for name in sorted(all_names):
        versions = {m: per_master[m][name] for m in per_master if name in per_master[m]}
        if len(set(versions.values())) > 1:
            drift[name] = versions

    result: dict = {
        'masters': {
            m.name: {'count': len(per_master.get(m.name, {})), 'core': core.get(m.name)}
            for m in get_fleet().masters
        },
        'drift': drift,
        'errors': errors,
    }
    if full:
        result['plugins'] = per_master
    return result
