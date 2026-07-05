"""Runner stdlib-only para los tests del módulo de agenda.

Permite ejecutar los unit tests de dominio, use cases y tools de agenda
en entornos SIN dependencias instaladas (no requiere pytest): inyecta un
shim mínimo de pytest y ejecuta los métodos test_* de los módulos nuevos.

Uso:
    python3 scripts/smoke_appointments.py

NO sustituye a `pytest tests/` — es un smoke check para sandboxes sin red.
"""

from __future__ import annotations

import asyncio
import inspect
import re
import sys
import traceback
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _install_pytest_shim() -> None:
    if "pytest" in sys.modules:
        return

    shim = types.ModuleType("pytest")

    class _Raises:
        def __init__(self, exc_type, match=None):
            self.exc_type = exc_type
            self.match = match

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                raise AssertionError(f"DID NOT RAISE {self.exc_type}")
            if not issubclass(exc_type, self.exc_type):
                return False
            if self.match and not re.search(self.match, str(exc)):
                raise AssertionError(
                    f"Pattern {self.match!r} not found in {str(exc)!r}"
                )
            return True

    class _Mark:
        @staticmethod
        def asyncio(fn=None, **kwargs):
            if fn is None:
                return lambda f: f
            return fn

        def __getattr__(self, name):
            return lambda fn: fn

    shim.raises = _Raises
    shim.mark = _Mark()
    sys.modules["pytest"] = shim


def _install_dependency_stubs() -> None:
    """Stubs mínimos para libs externas NO usadas por los tests de agenda.

    El paquete app.infrastructure.ai importa (vía __init__) módulos que
    requieren pydantic_settings/openai/langgraph. Los tests de agenda no
    los ejercitan, pero el import del paquete los necesita presentes.
    Solo se instala el stub si la lib real no está disponible.
    """

    def _try(name: str) -> bool:
        try:
            __import__(name)
            return True
        except ImportError:
            return False

    if not _try("pydantic_settings"):
        mod = types.ModuleType("pydantic_settings")

        class BaseSettings:  # noqa: D401 — stub
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        mod.BaseSettings = BaseSettings
        mod.SettingsConfigDict = dict
        sys.modules["pydantic_settings"] = mod

    if not _try("openai"):
        mod = types.ModuleType("openai")

        class AsyncOpenAI:
            def __init__(self, *args, **kwargs):
                pass

        mod.AsyncOpenAI = AsyncOpenAI
        sys.modules["openai"] = mod

    if not _try("langgraph.graph"):
        pkg = types.ModuleType("langgraph")
        graph = types.ModuleType("langgraph.graph")

        class StateGraph:
            def __init__(self, *args, **kwargs):
                pass

            def add_node(self, *a, **k):
                pass

            def add_edge(self, *a, **k):
                pass

            def add_conditional_edges(self, *a, **k):
                pass

            def set_entry_point(self, *a, **k):
                pass

            def compile(self):
                return self

        graph.StateGraph = StateGraph
        graph.END = "__end__"
        pkg.graph = graph
        sys.modules["langgraph"] = pkg
        sys.modules["langgraph.graph"] = graph


def main() -> int:
    _install_pytest_shim()
    _install_dependency_stubs()

    module_names = [
        "tests.unit.test_appointment_entity",
        "tests.unit.test_appointment_use_cases",
        "tests.unit.test_appointment_tools",
    ]

    passed = 0
    failed: list[tuple[str, str]] = []

    for module_name in module_names:
        module = __import__(module_name, fromlist=["*"])
        for cls_name, cls in inspect.getmembers(module, inspect.isclass):
            if not cls_name.startswith("Test"):
                continue
            for meth_name, meth in inspect.getmembers(cls, inspect.isfunction):
                if not meth_name.startswith("test_"):
                    continue
                test_id = f"{module_name}::{cls_name}::{meth_name}"
                try:
                    instance = cls()
                    result = getattr(instance, meth_name)()
                    if inspect.iscoroutine(result):
                        asyncio.run(result)
                    passed += 1
                except Exception:
                    failed.append((test_id, traceback.format_exc()))

    print(f"\n{passed} passed, {len(failed)} failed")
    for test_id, tb in failed:
        print(f"\nFAILED {test_id}\n{tb}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
