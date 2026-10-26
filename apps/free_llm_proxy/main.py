"""CLI Entrypoint for Free LLM Proxy server."""

import argparse
from pathlib import Path
import sys
import uvicorn

# Ensure repository root is in sys.path when invoked directly as a script
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from apps.free_llm_proxy import config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Free LLM Proxy: Unified free LLM endpoint"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.PORT,
        help=f"Port to listen on (default: {config.PORT})",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=config.HOST,
        help=f"Host to bind to (default: {config.HOST})",
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )

    args = parser.parse_args()
    print(f"🚀 Starting Free LLM Proxy on http://{args.host}:{args.port}")
    print(f"🔑 Master Key: {config.MASTER_KEY[:8]}...")
    print(f"📊 Metrics: http://{args.host}:{args.port}/v1/metrics")
    print(f"🩺 Health: http://{args.host}:{args.port}/health")

    uvicorn.run(
        "apps.free_llm_proxy.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
