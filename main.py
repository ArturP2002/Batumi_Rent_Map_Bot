"""Project entrypoint. Run from repository root:

    python main.py              # API + bot + worker + miniapp (default)
    python main.py all          # same as default
    python main.py api
    python main.py bot
    python main.py worker
    python main.py miniapp
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
MINIAPP = ROOT / "miniapp"
VENV_PYTHON = BACKEND / ".venv" / "bin" / "python"
ENV_FILE = ROOT / ".env"


def _ensure_project_venv() -> None:
    """Re-exec under backend/.venv so system Python is not required."""
    if os.environ.get("BRM_SKIP_VENV") == "1":
        return
    if not VENV_PYTHON.exists():
        raise SystemExit(
            "Не найден backend/.venv.\n"
            "Создай окружение:\n"
            "  cd backend && python3 -m venv .venv && source .venv/bin/activate "
            "&& pip install -e '.[dev]'"
        )
    current = Path(sys.executable).resolve()
    target = VENV_PYTHON.resolve()
    if current != target:
        os.execv(str(target), [str(target), str(ROOT / "main.py"), *sys.argv[1:]])


def _load_dotenv() -> None:
    """Load root .env into os.environ (does not override existing vars)."""
    if not ENV_FILE.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        # Minimal fallback if python-dotenv is missing
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)
        return
    load_dotenv(ENV_FILE, override=False)


def _prepare_env() -> None:
    os.chdir(ROOT)
    sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("ENV_FILE", str(ENV_FILE))
    _load_dotenv()


def _import_backend(module: str):
    """Load a backend package module (path is prepared in `_prepare_env`)."""
    import importlib

    return importlib.import_module(module)


def run_api(*, host: str = "0.0.0.0", port: int = 8001, reload: bool = True) -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        app_dir=str(BACKEND),
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
    )


def run_bot() -> None:
    bot_main = _import_backend("app.bot.main").main
    asyncio.run(bot_main())


def run_worker() -> None:
    worker_loop = _import_backend("app.tasks.worker").loop
    asyncio.run(worker_loop())


def _npm_cmd() -> str:
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm не найден. Установи Node.js, чтобы запускать Mini App.")
    return npm


def run_miniapp() -> None:
    if not (MINIAPP / "package.json").exists():
        raise SystemExit(f"Не найден Mini App: {MINIAPP}")
    if not (MINIAPP / "node_modules").exists():
        raise SystemExit(
            "Нет miniapp/node_modules.\n"
            "  cd miniapp && npm install"
        )
    npm = _npm_cmd()
    os.chdir(MINIAPP)
    os.execvp(npm, [npm, "run", "dev"])


def run_all(*, host: str = "0.0.0.0", port: int = 8001) -> None:
    """Start API, bot, worker and Mini App; stop all on Ctrl+C."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND) + os.pathsep + env.get("PYTHONPATH", "")
    env["ENV_FILE"] = str(ENV_FILE)
    env["BRM_SKIP_VENV"] = "1"
    children: list[tuple[str, subprocess.Popen]] = []

    def stop(*_args: object) -> None:
        for _name, proc in children:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
        for _name, proc in children:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    py = str(VENV_PYTHON if VENV_PYTHON.exists() else sys.executable)

    def spawn(name: str, args: list[str], *, cwd: Path = ROOT) -> None:
        proc = subprocess.Popen(args, cwd=str(cwd), env=env)
        children.append((name, proc))
        print(f"Started {name} (pid {proc.pid})")

    spawn(
        "api",
        [
            py,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--app-dir",
            str(BACKEND),
            *(["--env-file", str(ENV_FILE)] if ENV_FILE.exists() else []),
        ],
    )
    spawn("bot", [py, str(ROOT / "main.py"), "bot"])
    spawn("worker", [py, str(ROOT / "main.py"), "worker"])

    npm = shutil.which("npm")
    if npm and (MINIAPP / "node_modules").exists():
        spawn("miniapp", [npm, "run", "dev"], cwd=MINIAPP)
    else:
        print(
            "Mini App не запущен (нет npm или node_modules). "
            "Сделай: cd miniapp && npm install && npm run dev",
            file=sys.stderr,
        )

    print(f"API      http://127.0.0.1:{port}")
    print("Mini App http://127.0.0.1:5173  (ngrok → http://127.0.0.1:5173)")
    print("Bot + worker running. Ctrl+C to stop.")
    try:
        while True:
            for name, proc in children:
                code = proc.poll()
                if code is not None:
                    print(f"{name} exited with code {code}", file=sys.stderr)
                    stop()
                    raise SystemExit(code)
            time.sleep(1)
    except KeyboardInterrupt:
        stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Batumi Rent Map launcher")
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=("api", "bot", "worker", "miniapp", "all"),
        help="What to start (default: all = api + bot + worker + miniapp)",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("API_PORT", "8001")),
        help="API port (default 8001; 8000 is often busy)",
    )
    parser.add_argument("--no-reload", action="store_true")
    args = parser.parse_args()

    _prepare_env()

    if args.command == "api":
        run_api(host=args.host, port=args.port, reload=not args.no_reload)
    elif args.command == "bot":
        run_bot()
    elif args.command == "worker":
        run_worker()
    elif args.command == "miniapp":
        run_miniapp()
    elif args.command == "all":
        run_all(host=args.host, port=args.port)


if __name__ == "__main__":
    _ensure_project_venv()
    main()
