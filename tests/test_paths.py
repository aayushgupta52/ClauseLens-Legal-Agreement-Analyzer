from clauselens import paths


def test_repo_layout_exists():
    assert paths.ROOT.is_dir()
    assert (paths.CONFIGS / "scope.yaml").is_file()
    assert paths.RAW.parent == paths.DATA
