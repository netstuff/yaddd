"""Command-line entrypoint for rendering yaddd scenarios as Mermaid diagrams."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Protocol, Sequence

from yaddd_utils.inspect.scenario import ScenarioAnalyzer, ScenarioInfo
from yaddd_utils.mermaid._adapter import MermaidAdapterError, save_image
from yaddd_utils.mermaid.graph import ScenarioGraphRenderer
from yaddd_utils.mermaid.renderers import Renderer, RenderOptions
from yaddd_utils.mermaid.scenario import ScenarioRenderer
from yaddd_utils.mermaid.sequence import ScenarioSequenceRenderer


class _RendererFactory(Protocol):
    def __call__(self, options: RenderOptions | None = None) -> Renderer: ...


_RENDERERS: dict[str, _RendererFactory] = {
    "flowchart": ScenarioRenderer,
    "graph": ScenarioGraphRenderer,
    "sequence": ScenarioSequenceRenderer,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yaddd-mermaid",
        description="Render yaddd scenarios as Mermaid diagrams.",
    )
    parser.add_argument(
        "modules",
        nargs="+",
        help="Python module paths to inspect (e.g. myapp.scenarios).",
    )
    parser.add_argument(
        "--renderer",
        choices=list(_RENDERERS.keys()),
        default="flowchart",
        help="Diagram type to render (default: flowchart).",
    )
    parser.add_argument(
        "--direction",
        default="TD",
        help="Flowchart direction: TD, LR, RL, BT (default: TD).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write the diagram to this file instead of stdout.",
    )
    parser.add_argument(
        "--image",
        type=Path,
        help="Also render the diagram to an image (png/svg/pdf) using mermaid-py.",
    )
    parser.add_argument(
        "--show-levels",
        action="store_true",
        help="Include step log levels in node labels.",
    )
    parser.add_argument(
        "--hide-conditions",
        action="store_true",
        help="Do not annotate conditional steps.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return an exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    analyzer = ScenarioAnalyzer()
    scenarios: list[ScenarioInfo] = []
    for module_name in args.modules:
        scenarios.extend(analyzer.analyze_module(module_name))

    if not scenarios:
        print("No Scenario subclasses found.", file=sys.stderr)
        return 1

    options = RenderOptions(
        direction=args.direction,
        show_levels=args.show_levels,
        show_conditions=not args.hide_conditions,
    )
    renderer_cls = _RENDERERS[args.renderer]
    renderer = renderer_cls(options)
    diagram = renderer.render_infos(scenarios)

    if args.output:
        args.output.write_text(diagram, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(diagram)

    if args.image:
        try:
            save_image(diagram, args.image)
            print(f"Wrote image {args.image}")
        except MermaidAdapterError as exc:
            print(f"Image rendering failed: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
