from create_release_agent.tests import discover_validation_command


def test_discover_validation_defaults_to_pytest(tmp_path):
    assert discover_validation_command(tmp_path) == ["pytest"]
