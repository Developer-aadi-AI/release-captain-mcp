from create_release_agent.changelog import Entry, Section, classify, compute_next_version, render_changelog


def test_classify_added():
    assert classify("feat: add support for foo") == Section.ADDED


def test_classify_fixed():
    assert classify("fix: handle bar") == Section.FIXED


def test_classify_breaking():
    assert classify("feat!: remove old api") == Section.BREAKING


def test_compute_next_version_initial_release():
    assert compute_next_version(None, []) == "0.1.0"


def test_compute_next_version_feature_bump():
    assert compute_next_version("1.2.3", [Entry(Section.ADDED, "feat", "x")]) == "1.3.0"


def test_render_changelog_groups_sections():
    body = render_changelog(
        [
            Entry(Section.ADDED, "add foo", "x"),
            Entry(Section.FIXED, "fix bar", "y"),
        ],
        "owner/repo",
    )
    assert "## Added" in body
    assert "## Fixed" in body
    assert "add foo" in body
    assert "fix bar" in body
