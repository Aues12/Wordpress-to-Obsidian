from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from assembler import assemble
from cli.main import order_and_limit_posts, write_order
from config.loader import load_config
from core.models import DocumentUnit, Post
from importer.wordpress_api import ensure_json_export
from processors.pipeline import process_posts
from sources.imported_json import load_imported_json
from writer import write


CONFIG_PATH = Path("config.json")
config = load_config(str(CONFIG_PATH))
JSON_PATH = Path(config["paths"]["json_file"])
OUTPUT_DIR = config["paths"].get("output_dir", "output")
BASE_URL = config["wordpress"]["base_url"]
DEFAULT_FRONTMATTER = config["frontmatter"]["include_frontmatter"]
UNSET = object()

DEFAULT_USAGE_PROFILE = {
    "refresh": False,
    "order": "newest",
    "limit": None,
    "write_order": "oldest",
    "mode": "per_post",
    "include_frontmatter": DEFAULT_FRONTMATTER,
    "format": "md",
    "output_dir": OUTPUT_DIR,
}


def load_usage_profile() -> dict:
    profile = config.get("usage_profile", {})
    if not isinstance(profile, dict):
        profile = {}

    loaded_profile = DEFAULT_USAGE_PROFILE.copy()
    loaded_profile.update(
        {
            key: profile[key]
            for key in DEFAULT_USAGE_PROFILE
            if key in profile
        }
    )

    return loaded_profile


USAGE_PROFILE = load_usage_profile()


@dataclass
class CommandSession:
    posts: list[Post] | None = None
    units: list[DocumentUnit] | None = None
    refresh: bool = USAGE_PROFILE["refresh"]
    order: str = USAGE_PROFILE["order"]
    limit: int | None = USAGE_PROFILE["limit"]
    write_order_value: str = USAGE_PROFILE["write_order"]
    mode: str = USAGE_PROFILE["mode"]
    include_frontmatter: bool = USAGE_PROFILE["include_frontmatter"]
    output_format: str = USAGE_PROFILE["format"]
    output_dir: str = USAGE_PROFILE["output_dir"]


def build_usage_profile(session: CommandSession) -> dict:
    return {
        "refresh": session.refresh,
        "order": session.order,
        "limit": session.limit,
        "write_order": session.write_order_value,
        "mode": session.mode,
        "include_frontmatter": session.include_frontmatter,
        "format": session.output_format,
        "output_dir": session.output_dir,
    }


def save_usage_profile(session: CommandSession) -> bool:
    try:
        config_data = load_config(str(CONFIG_PATH))
        config_data["usage_profile"] = build_usage_profile(session)

        with CONFIG_PATH.open("w", encoding="utf-8") as handle:
            json.dump(config_data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except Exception as exc:
        print(f"[WARN] Could not save last used settings: {exc}")
        return False

    return True


def prompt_text(message: str) -> str:
    while True:
        try:
            return input(message).strip()
        except KeyboardInterrupt:
            print("\n[WARN] Input interrupted. Please try again or type 'quit'.")
        except EOFError as exc:
            raise SystemExit("\nExiting commander.") from exc


def prompt_yes_no(message: str, default: bool | None = None) -> bool:
    if default is True:
        suffix = " [Y/n]: "
    elif default is False:
        suffix = " [y/N]: "
    else:
        suffix = " [y/n]: "

    while True:
        raw = prompt_text(f"{message}{suffix}").lower()

        if not raw and default is not None:
            return default

        if raw in {"y", "yes"}:
            return True

        if raw in {"n", "no"}:
            return False

        print("Please enter 'y' or 'n'.")


def prompt_yes_no_menu(message: str, default: bool = True) -> bool:
    default_label = "Yes" if default else "No"

    print(f"\n{message}")
    print("1) Yes")
    print("2) No")
    print(f"Press Enter for {default_label}.")

    while True:
        raw = prompt_text("> ").lower()

        if not raw:
            return default

        if raw in {"1", "y", "yes"}:
            return True

        if raw in {"2", "n", "no"}:
            return False

        print("Please choose 1 for Yes, 2 for No, or press Enter for the default.")


def prompt_choice(message: str, choices: list[str], default: str | None = None) -> str:
    normalized_choices = {choice.lower(): choice for choice in choices}
    options = "/".join(choices)
    suffix = f" [{default}]" if default else ""

    while True:
        raw = prompt_text(f"{message} ({options}){suffix}: ").lower()

        if not raw and default is not None:
            return default

        if raw in normalized_choices:
            return normalized_choices[raw]

        print(f"Please enter one of: {', '.join(choices)}")


def prompt_limit(default: int | None = None) -> int | None:
    default_label = "all" if default is None else str(default)

    while True:
        raw = prompt_text(f"limit? (integer or all) [{default_label}]: ").lower()

        if not raw:
            return default

        if raw == "all":
            return None

        try:
            value = int(raw)
        except ValueError:
            print("Please enter a positive integer or 'all'.")
            continue

        if value <= 0:
            print("Limit must be greater than zero, or use 'all'.")
            continue

        return value


def prompt_menu_choice() -> str:
    print("\nSelect mode:")
    print("1) pipeline")
    print("2) commander")
    print("3) help")
    print("4) quit")

    mapping = {
        "1": "pipeline",
        "2": "commander",
        "3": "help",
        "4": "quit",
    }

    while True:
        raw = prompt_text("> ").lower()

        if raw in mapping:
            return mapping[raw]

        if raw in mapping.values():
            return raw

        print("Please choose 1, 2, 3, or 4.")


def show_startup_help() -> None:
    print("\nModes:")
    print("  pipeline  - Run every step in order with guided prompts.")
    print("  commander - Open an interactive shell and run steps manually.")
    print("  help      - Show this help.")
    print("  quit      - Exit the program.")


def show_commander_help() -> None:
    print("\nAvailable commands:")
    print("  help         Show this help menu.")
    print("  status       Show current session state.")
    print("  pipeline     Run the full pipeline in guided order.")
    print("  export_json  Fetch or reuse the WordPress JSON export.")
    print("  load         Load posts from the imported JSON file.")
    print("  process      Process the loaded posts.")
    print("  order_limit  Apply load-order sorting and an optional limit.")
    print("  write_order  Reorder posts for writing output.")
    print("  assemble     Build document units from prepared posts.")
    print("  write        Write assembled units to markdown files.")
    print("  quit         Leave commander mode.")


def print_status(session: CommandSession) -> None:
    posts_label = "none" if session.posts is None else str(len(session.posts))
    units_label = "none" if session.units is None else str(len(session.units))
    limit_label = "all" if session.limit is None else str(session.limit)
    frontmatter_label = "yes" if session.include_frontmatter else "no"

    print("\nSession status:")
    print(f"  posts: {posts_label}")
    print(f"  units: {units_label}")
    print(f"  order: {session.order}")
    print(f"  limit: {limit_label}")
    print(f"  write_order: {session.write_order_value}")
    print(f"  mode: {session.mode}")
    print(f"  include_frontmatter: {frontmatter_label}")
    print(f"  format: {session.output_format}")
    print(f"  output_dir: {session.output_dir}")


def require_posts(session: CommandSession, command_name: str) -> bool:
    if session.posts is not None:
        return True

    print(f"[WARN] '{command_name}' requires posts in session.")
    print("       Run 'load' first, then continue with the next steps.")
    return False


def require_units(session: CommandSession, command_name: str) -> bool:
    if session.units is not None:
        return True

    print(f"[WARN] '{command_name}' requires assembled units in session.")
    print("       Run 'assemble' after your posts are ready.")
    return False


def command_export_json(
    session: CommandSession,
    refresh: bool | None = None,
    prompt_for_parameters: bool = True,
) -> None:
    if refresh is not None:
        refresh_value = refresh
    elif prompt_for_parameters:
        refresh_value = prompt_yes_no("refresh?", default=session.refresh)
    else:
        refresh_value = session.refresh

    ensure_json_export(
        base_url=BASE_URL,
        json_path=JSON_PATH,
        refresh=refresh_value,
    )

    if refresh_value:
        session.posts = None
        session.units = None
        print("[INFO] Session posts/units cleared because the source JSON was refreshed.")

    session.refresh = refresh_value


def command_load(session: CommandSession) -> None:
    posts = load_imported_json(input_file=JSON_PATH, verbose=True)
    session.posts = posts
    session.units = None
    print(f"[INFO] Loaded {len(posts)} posts into session.")


def command_process(session: CommandSession) -> None:
    if not require_posts(session, "process"):
        return

    session.posts = process_posts(session.posts, verbose=True)
    session.units = None


def command_order_limit(
    session: CommandSession,
    order: str | None = None,
    limit: int | None | object = UNSET,
    prompt_for_parameters: bool = True,
) -> None:
    if not require_posts(session, "order_limit"):
        return

    if order is not None:
        order_value = order
    elif prompt_for_parameters:
        order_value = prompt_choice(
            "order?",
            choices=["newest", "oldest"],
            default=session.order,
        )
    else:
        order_value = session.order

    if limit is UNSET and prompt_for_parameters and order is None:
        limit_value = prompt_limit(default=session.limit)
    elif limit is UNSET:
        limit_value = session.limit
    else:
        limit_value = limit

    session.posts = order_and_limit_posts(
        session.posts,
        order=order_value,
        limit=limit_value,
    )
    session.units = None
    session.order = order_value
    session.limit = limit_value
    limit_label = "all" if limit_value is None else str(limit_value)
    print(f"[INFO] Posts ordered as '{order_value}' with limit={limit_label}.")


def command_write_order(
    session: CommandSession,
    order: str | None = None,
    prompt_for_parameters: bool = True,
) -> None:
    if not require_posts(session, "write_order"):
        return

    if order is not None:
        order_value = order
    elif prompt_for_parameters:
        order_value = prompt_choice(
            "write_order?",
            choices=["newest", "oldest"],
            default=session.write_order_value,
        )
    else:
        order_value = session.write_order_value

    session.posts = write_order(session.posts, order=order_value)
    session.units = None
    session.write_order_value = order_value
    print(f"[INFO] Posts reordered for writing: {order_value}.")


def command_assemble(
    session: CommandSession,
    mode: str | None = None,
    include_frontmatter: bool | None = None,
    prompt_for_parameters: bool = True,
) -> None:
    if not require_posts(session, "assemble"):
        return

    if mode is not None:
        mode_value = mode
    elif prompt_for_parameters:
        mode_value = prompt_choice(
            "mode?",
            choices=["per_post", "book"],
            default=session.mode,
        )
    else:
        mode_value = session.mode

    if include_frontmatter is not None:
        frontmatter_value = include_frontmatter
    elif prompt_for_parameters:
        frontmatter_value = prompt_yes_no(
            "include frontmatter?",
            default=session.include_frontmatter,
        )
    else:
        frontmatter_value = session.include_frontmatter

    # assemble() mutates post content when frontmatter is included, so we
    # assemble a snapshot to keep the session posts reusable across commands.
    posts_snapshot = deepcopy(session.posts)
    units = assemble(
        posts_snapshot,
        mode=mode_value,
        verbose=True,
        include_frontmatter=frontmatter_value,
    )

    session.units = units
    session.mode = mode_value
    session.include_frontmatter = frontmatter_value
    print(f"[INFO] Prepared {len(units)} document units.")


def command_write(session: CommandSession) -> None:
    if not require_units(session, "write"):
        return

    print(f"[INFO] Writing {len(session.units)} markdown files...")
    print(f"[INFO] Output mode: {session.mode}")
    write(
        session.units,
        format=session.output_format,
        output_dir=session.output_dir,
        verbose=True,
    )
    if save_usage_profile(session):
        print("[INFO] Saved last used settings.")


def run_full_pipeline(
    session: CommandSession,
    prompt_for_parameters: bool = False,
) -> None:
    print("\nStarting guided pipeline...")

    command_export_json(session, prompt_for_parameters=prompt_for_parameters)

    print("Starting build...")
    command_load(session)
    command_process(session)
    command_order_limit(session, prompt_for_parameters=prompt_for_parameters)
    command_write_order(session, prompt_for_parameters=prompt_for_parameters)
    command_assemble(session, prompt_for_parameters=prompt_for_parameters)
    command_write(session)

    print("Build completed. ✅")


def run_commander(session: CommandSession) -> None:
    print("\nCommander mode. Type 'help' for available commands.")

    commands = {
        "help": lambda current: show_commander_help(),
        "status": print_status,
        "pipeline": lambda current: run_full_pipeline(
            current,
            prompt_for_parameters=True,
        ),
        "export_json": command_export_json,
        "load": command_load,
        "process": command_process,
        "order_limit": command_order_limit,
        "write_order": command_write_order,
        "assemble": command_assemble,
        "write": command_write,
    }

    while True:
        raw_command = prompt_text("\ncommander> ").lower()

        if not raw_command:
            continue

        if raw_command == "quit":
            print("Leaving commander mode.")
            return

        handler = commands.get(raw_command)
        if handler is None:
            print(f"[WARN] Unknown command: {raw_command}")
            print("       Type 'help' to see the available commands.")
            continue

        try:
            handler(session)
        except Exception as exc:
            print(f"[ERROR] Command '{raw_command}' failed: {exc}")


def main() -> None:
    session = CommandSession()

    if prompt_yes_no_menu("Run with last used settings?", default=True):
        try:
            run_full_pipeline(session)
        except Exception as exc:
            print(f"[ERROR] Pipeline failed: {exc}")
        return

    while True:
        selection = prompt_menu_choice()

        if selection == "pipeline":
            try:
                run_full_pipeline(session, prompt_for_parameters=True)
            except Exception as exc:
                print(f"[ERROR] Pipeline failed: {exc}")
            continue

        if selection == "commander":
            run_commander(session)
            continue

        if selection == "help":
            show_startup_help()
            continue

        print("Goodbye.")
        return


if __name__ == "__main__":
    main()
