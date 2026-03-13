from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_DIR = REPO_ROOT / "deploy"


def _kustomization_resources(path: Path) -> list[str]:
    resources: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            resources.append(stripped[2:].strip())
    return resources


def _manifest_kinds(path: Path) -> set[str]:
    kinds: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("kind:"):
            kinds.add(stripped.split(":", maxsplit=1)[1].strip())
    return kinds


def test_overlays_define_only_environment_configuration():
    dev_resources = _kustomization_resources(DEPLOY_DIR / "development" / "kustomization.yaml")
    prod_resources = _kustomization_resources(DEPLOY_DIR / "production" / "kustomization.yaml")

    expected_overlay_resources = [
        "../base",
        "api-configmap.yaml",
        "api-secret.yaml",
        "postgres-configmap.yaml",
        "postgres-secret.yaml",
        "minio-secret.yaml",
    ]

    assert dev_resources == expected_overlay_resources
    assert prod_resources == expected_overlay_resources


def test_base_contains_shared_workloads_only():
    base_manifest_paths = [
        DEPLOY_DIR / "base" / "api.yaml",
        DEPLOY_DIR / "base" / "postgres.yaml",
        DEPLOY_DIR / "base" / "minio.yaml",
    ]

    for manifest_path in base_manifest_paths:
        kinds = _manifest_kinds(manifest_path)
        assert "ConfigMap" not in kinds
        assert "Secret" not in kinds
