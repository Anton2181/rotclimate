import pytest

from scripts.package_fit_atlases import page_dependencies


def test_packager_follows_release_report_and_nested_pages(tmp_path):
    atlas = tmp_path / 'atlases'; atlas.mkdir()
    reports = tmp_path / 'reports'; reports.mkdir()
    release = reports / 'New release.md'; release.write_text('Latest adopted physics')
    index = atlas / 'index.html'
    index.write_text('<a href="detail.html">Details</a><a href="#map">Map</a>')
    detail = atlas / 'detail.html'
    detail.write_text('<a href="../reports/New%20release.md">Release</a>'
                      '<a href="index.html">Back</a><img src="https://example.org/remote.png">')
    assert set(page_dependencies([index], tmp_path)) == {index, detail, release}


def test_packager_reports_broken_link_before_writing_a_bundle(tmp_path):
    page = tmp_path / 'index.html'; page.write_text('<a href="missing.md">Missing</a>')
    with pytest.raises(ValueError, match='Broken local atlas link'):
        page_dependencies([page], tmp_path)
