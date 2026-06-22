"""A self-describing usage guide, exposed as the get_readme tool.

Lets an MCP client learn this server's capabilities, the configured master fleet, how to
select a master per call, sample queries, and tips, without guessing or reaching for an
external Jenkins CLI. The master fleet is injected live from the loaded config.
"""

from mcp_jenkins.core.fleet import get_fleet
from mcp_jenkins.server import mcp

_GUIDE = [
    '# Jenkins MCP — read-only fleet access (start here)',
    '',
    "Token-free, read-only gateway to Percona's Jenkins masters. You log in once via Authentik",
    '(Duo) in the browser; the server holds the Jenkins credentials, so you never handle a token.',
    'Every tool is read-only: no triggering, stopping, or reconfiguring builds (use the Jenkins UI',
    'for that).',
    '',
    '__FLEET__',
    'Call list_masters() for live reachability and Jenkins core versions.',
    '',
    '## Pick a master (per call)',
    'Every per-master tool takes an optional `master` argument:',
    '  - omit it       -> the default master (the one pinned in your MCP config, else the server default)',
    '  - master="pxc"  -> target that master for this one call (must be a configured name above)',
    'These tools cover read access across the whole fleet; there is no separate Jenkins CLI to reach for.',
    '',
    '## Tools',
    'Jobs:',
    '  - get_all_items(limit?, master?)          flat compact list of jobs/folders (fullname/class/color)',
    '  - query_items(fullname_pattern?, color_pattern?, class_pattern?, folder_depth?, limit?, master?)',
    '        filter jobs by name/class/color; flat compact list. Both return {items, total, truncated}.',
    '  - get_item(fullname, master?)             one job/folder',
    '  - get_item_config(fullname, master?)      job config XML',
    '  - get_item_parameters(fullname, master?)  the build parameters a job accepts',
    'Builds:',
    '  - get_running_builds(master?)             what is building now',
    '  - get_build(fullname, number?, master?)   build result/info (last build if number omitted)',
    '  - get_build_console_output(fullname, number?, pattern?, offset?, limit?, master?)',
    '        console log; pattern is a regex line filter (slice big logs with pattern/limit)',
    '  - get_build_test_report / get_build_parameters / get_build_scripts(fullname, number?, master?)',
    '  - get_all_build_artifacts / get_build_artifact / get_build_artifact_url(fullname, ..., master?)',
    '  - get_build_history(fullname, count?, master?)     recent builds (number/result/timestamp/duration)',
    '  - get_build_stages(fullname, number?, master?)     pipeline stage breakdown (empty for freestyle)',
    '  - get_build_changeset(fullname, number?, master?)  SCM commits included in a build',
    'Search:',
    '  - search_build_logs(pattern, job_pattern, master?, ...)  grep build consoles across jobs (cost-bounded)',
    'Infra:',
    '  - get_all_nodes / get_node / get_node_config(name?, master?)   build agents',
    '  - get_all_queue_items / get_queue_item(id?, master?)           build queue',
    '  - get_all_views / get_view(view_path, depth?, master?)         views',
    '',
    '## Sample queries',
    '  "which masters are up?"                       -> list_masters()',
    '  "what jobs are on pxc?"                        -> get_all_items(master="pxc")',
    '  "pxc jobs (incl. folders) matching 8.0"        -> query_items(fullname_pattern=".*8.0.*", master="pxc")',
    '  "did the last build of <job> pass?"            -> get_build(fullname="<job>")',
    '  "console for <job> build 123"                  -> get_build_console_output(fullname="<job>", number=123)',
    '  "just the errors in a log"   -> get_build_console_output(fullname="<job>", pattern="(?i)error|fail")',
    '  "what parameters does <job> take?"             -> get_item_parameters(fullname="<job>")',
    '  "what is running on ps80 right now?"           -> get_running_builds(master="ps80")',
    '  "last 10 builds of <job>"  -> get_build_history(fullname="<job>", count=10)',
    '  "which stage failed in <job>?"  -> get_build_stages(fullname="<job>")',
    '  "what changed in <job> build 50?"  -> get_build_changeset(fullname="<job>", number=50)',
    '  "find OOMKilled in pxc jobs"  -> search_build_logs(pattern="OOMKilled", job_pattern="pxc.*", master="pxc")',
    '',
    '## Tips',
    '  - Job names are FULL paths incl. folders, e.g. "PXC/pxc-8.0/build". Discover exact names with query_items.',
    '  - get_all_items / query_items return a flat compact list capped by limit (total + truncated reported).',
    '  - On a big master, narrow with query_items(fullname_pattern=...) rather than raising limit.',
    '  - number defaults to the most recent build when omitted.',
    '  - Read-only by design: there is intentionally no build/trigger/config tool here.',
]


@mcp.tool(tags=['read'])
def get_readme() -> str:
    """Start here: how to use this read-only Jenkins fleet MCP.

    Returns a concise guide covering what this server is, the configured masters, how to select a
    master per call (the optional `master` argument), the full read-only tool catalog, sample
    natural-language queries mapped to tools, and tips. Call this first whenever you are unsure
    which tool to use or how to query the Jenkins fleet.
    """
    fleet = ', '.join(get_fleet().names()) or '(none configured)'
    return '\n'.join(f'Masters configured: {fleet}' if line == '__FLEET__' else line for line in _GUIDE)
