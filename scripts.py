# scripts.py
import sys

from avcfastapi.core.utils.commands.script_runner import ScriptRunner

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts.py <command_name> [options]")
        sys.exit(1)

    command_name = sys.argv[1]
    argv = sys.argv[2:]  # pass the rest of the args
    runner = ScriptRunner(commands_folder="scripts")
    runner.run(command_name, argv)
