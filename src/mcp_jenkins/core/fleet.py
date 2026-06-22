"""Fleet configuration: the masters this server can reach and their read-only credentials.

The server holds the Jenkins credentials (one read-only token per master), so MCP clients
never supply them. Tools select a master by NAME; only names present in this config are
reachable, which is the allowlist. The config is sourced from MCP_JENKINS_FLEET_FILE (a JSON
file, in production the ESO-mounted secret) or MCP_JENKINS_FLEET (inline JSON for local dev).
"""

import json
import os
from functools import lru_cache
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, SecretStr

from mcp_jenkins.jenkins import Jenkins


class Master(BaseModel):
    name: str
    url: str
    username: str
    token: SecretStr
    verify_ssl: bool = True


class Fleet(BaseModel):
    masters: list[Master] = []
    timeout: int = 30

    def names(self) -> list[str]:
        return [m.name for m in self.masters]

    def get(self, name: str) -> Master | None:
        return next((m for m in self.masters if m.name == name), None)


def _load_raw() -> dict:
    file_path = os.getenv('MCP_JENKINS_FLEET_FILE')
    if file_path:
        return json.loads(Path(file_path).read_text())
    inline = os.getenv('MCP_JENKINS_FLEET')
    if inline:
        return json.loads(inline)
    return {'masters': []}


@lru_cache(maxsize=1)
def get_fleet() -> Fleet:
    fleet = Fleet.model_validate(_load_raw())
    logger.info(f'Loaded fleet config with {len(fleet.masters)} master(s): {fleet.names()}')
    return fleet


def client_for(name: str) -> Jenkins:
    """Build a Jenkins client for a configured master, injecting the server-held read-only token.

    Raises ValueError if the name is not in the fleet config (the allowlist).
    """
    fleet = get_fleet()
    master = fleet.get(name)
    if master is None:
        msg = f'Unknown master {name!r}. Configured masters: {fleet.names()}'
        raise ValueError(msg)
    return Jenkins(
        url=master.url,
        username=master.username,
        password=master.token.get_secret_value(),
        timeout=fleet.timeout,
        verify_ssl=master.verify_ssl,
    )
