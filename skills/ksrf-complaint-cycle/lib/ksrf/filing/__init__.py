"""Fail-closed контур подготовки материалов для жалобы в КС РФ."""

from importlib import import_module

from .capabilities import diagnose_capabilities, doctor, load_capability_manifest
from .matter import initialize_matter, matter_status, register_input


_LAZY_WORKFLOW_EXPORTS = {
    "WorkflowError",
    "WorkflowInputError",
    "WorkflowRouter",
    "load_versioned_payload",
    "render_workflow_result",
    "workflow_exit_code",
}


def __getattr__(name: str):
    """Load the workflow only when requested; document libraries stay optional."""

    if name in _LAZY_WORKFLOW_EXPORTS:
        module = import_module(".workflow", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "WorkflowError",
    "WorkflowInputError",
    "WorkflowRouter",
    "diagnose_capabilities",
    "doctor",
    "initialize_matter",
    "load_versioned_payload",
    "load_capability_manifest",
    "matter_status",
    "render_workflow_result",
    "register_input",
    "workflow_exit_code",
]
