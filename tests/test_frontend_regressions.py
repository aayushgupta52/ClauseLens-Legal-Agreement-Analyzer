from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mobile_language_toggle_is_not_hidden():
    css = (ROOT / "frontend/src/styles.css").read_text(encoding="utf-8")
    mobile = css.split("@media (max-width:760px)", 1)[1].split("@media (max-width:420px)", 1)[0]
    tiny = css.split("@media (max-width:420px)", 1)[1].split("@media (prefers-reduced-motion", 1)[0]
    assert ".language-switch{display:flex" in mobile
    assert ".language-switch{display:flex" in tiny
    assert ".global-search{display:none}" in tiny


def test_property_purchase_labels_and_sample_option_exist():
    app = (ROOT / "frontend/src/App.jsx").read_text(encoding="utf-8")
    i18n = (ROOT / "frontend/src/i18n.js").read_text(encoding="utf-8")
    assert "property_specifications:" in app
    assert "value=\"property_purchase\"" in app
    assert "'Home purchase agreement': 'घर खरीद समझौता'" in i18n


def test_render_docker_build_does_not_require_missing_lockfile():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY frontend/package.json frontend/package-lock.json ./" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "RUN npm run build" in dockerfile