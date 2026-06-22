import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import get_http_request
from loguru import logger
from pydantic import BaseModel

from mcp_jenkins.core.fleet import client_for, get_fleet
from mcp_jenkins.jenkins import Jenkins


class LifespanContext(BaseModel):
    # The master used by per-master tools when the client sends no x-jenkins-master header.
    default_master: str | None = None
    jenkins_session_singleton: bool = True


@asynccontextmanager
async def lifespan(app: FastMCP[LifespanContext]) -> AsyncIterator['LifespanContext']:
    yield LifespanContext(
        default_master=os.getenv('jenkins_master') or None,
        jenkins_session_singleton=os.getenv('jenkins_session_singleton', 'true').lower() == 'true',
    )


def _selected_master(ctx: Context) -> str:
    """Resolve which master a per-master tool targets, by NAME (never client credentials).

    Priority: the x-jenkins-master request header, then the configured default, then the sole
    configured master. The name is validated against the fleet allowlist inside client_for.
    """
    name = None
    try:
        name = getattr(get_http_request().state, 'jenkins_master', None)
    except RuntimeError:
        pass  # no HTTP request context (e.g. stdio transport)
    except Exception as e:  # noqa: BLE001
        logger.error(f'Unexpected error reading request state: {e}')

    name = name or ctx.request_context.lifespan_context.default_master
    if not name:
        masters = get_fleet().masters
        if len(masters) == 1:
            return masters[0].name
        msg = (
            'No Jenkins master selected. Send the x-jenkins-master header, set the jenkins_master '
            f'default, or configure exactly one master in the fleet. Configured: {get_fleet().names()}'
        )
        raise ValueError(msg)
    return name


def jenkins(ctx: Context) -> Jenkins:
    """Return a Jenkins client for the selected master, with server-held read-only credentials."""
    name = _selected_master(ctx)
    singleton = ctx.request_context.lifespan_context.jenkins_session_singleton

    if singleton:
        cache = getattr(ctx.session, 'jenkins_clients', None)
        if not isinstance(cache, dict):
            cache = {}
            ctx.session.jenkins_clients = cache
        if name in cache:
            return cache[name]

    client = client_for(name)
    if singleton:
        ctx.session.jenkins_clients[name] = client
    return client
