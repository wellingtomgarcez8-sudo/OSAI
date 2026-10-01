from osai.ai.planner import build_spec
from osai.generator.compiler import compile_project
from osai.validation.project import validate_project


def test_generated_project_preserves_hardware_stack(tmp_path) -> None:
    spec = build_spec("TestOS", "KDE gaming with Wi-Fi, Bluetooth and Vulkan", [])
    project = compile_project(spec, tmp_path)
    packages = (project / "config/package-lists/osai.list.chroot").read_text()
    assert "linux-image-amd64" in packages
    assert "firmware-linux" in packages
    assert "network-manager" in packages
    assert "mesa-vulkan-drivers" in packages
    result = validate_project(project)
    assert result.ok, result.errors
