from mcp_jenkins.core.fleet import Fleet, Master
from mcp_jenkins.server import readme


def test_get_readme_lists_fleet_and_key_sections(mocker):
    mocker.patch(
        'mcp_jenkins.server.readme.get_fleet',
        return_value=Fleet(
            masters=[
                Master(name='ps80', url='u', username='u', token='x'),  # noqa: S106
                Master(name='pxc', url='u', username='u', token='x'),  # noqa: S106
            ]
        ),
    )

    text = readme.get_readme()

    assert 'Masters configured: ps80, pxc' in text
    assert 'master="pxc"' in text  # documents per-call selection
    assert 'list_masters()' in text
    assert 'query_items' in text
    assert 'read-only' in text.lower()


def test_get_readme_handles_empty_fleet(mocker):
    mocker.patch('mcp_jenkins.server.readme.get_fleet', return_value=Fleet(masters=[]))

    assert '(none configured)' in readme.get_readme()
