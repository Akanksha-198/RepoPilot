#validator.py

from pathlib import Path
import subprocess


def run_command(
    command: list[str],
    working_directory: str,
    timeout: int = 120
) -> dict:
    """
    Run a validation command inside the repository.
    """

    try:
        result = subprocess.run(
            command,
            cwd=working_directory,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            "command": command,
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except subprocess.TimeoutExpired as error:

        return {
            "command": command,
            "return_code": -1,
            "success": False,
            "stdout": "",
            "stderr": (
                f"Validation timed out after "
                f"{timeout} seconds."
            )
        }

    except Exception as error:

        return {
            "command": command,
            "return_code": -1,
            "success": False,
            "stdout": "",
            "stderr": str(error)
        }


def detect_project_type(
    repository_path: str
) -> str:
    """
    Detect the project type using
    common project configuration files.
    """

    repo_path = Path(
        repository_path
    ).resolve()

    # JavaScript / Node.js project
    if (repo_path / "package.json").exists():
        return "javascript"

    # Python project
    if (
        (repo_path / "requirements.txt").exists()
        or (repo_path / "pyproject.toml").exists()
    ):
        return "python"

    return "unknown"


def validate_repository(
    repository_path: str
) -> dict:
    """
    Validate the repository.

    Possible statuses:

    passed
    failed
    skipped
    """

    project_type = detect_project_type(
        repository_path
    )

    results = []

    # --------------------------------------------------------
    # PYTHON
    # --------------------------------------------------------

    if project_type == "python":

        result = run_command(
            [
                "python",
                "-m",
                "compileall",
                "."
            ],
            repository_path
        )

        results.append(result)

    # --------------------------------------------------------
    # JAVASCRIPT / NODE.JS
    # --------------------------------------------------------

    elif project_type == "javascript":

        package_json = Path(
            repository_path
        ) / "package.json"

        if package_json.exists():

            result = run_command(
                [
                    "npm.cmd",
                    "run",
                    "build"
                ],
                repository_path
            )

            results.append(result)

    # --------------------------------------------------------
    # UNKNOWN PROJECT
    # --------------------------------------------------------

    else:

        return {
            "status": "skipped",
            "success": False,
            "project_type": "unknown",
            "results": [],
            "reason": (
                "No supported project "
                "validation configuration "
                "was detected."
            )
        }

    # --------------------------------------------------------
    # NO VALIDATION RESULT
    # --------------------------------------------------------

    if not results:

        return {
            "status": "skipped",
            "success": False,
            "project_type": project_type,
            "results": [],
            "reason": (
                "No validation command "
                "was available."
            )
        }

    # --------------------------------------------------------
    # CHECK RESULTS
    # --------------------------------------------------------

    validation_passed = all(
        result["success"]
        for result in results
    )

    if validation_passed:

        return {
            "status": "passed",
            "success": True,
            "project_type": project_type,
            "results": results
        }

    return {
        "status": "failed",
        "success": False,
        "project_type": project_type,
        "results": results
    }


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("          RepoPilot - Phase 5A")
    print("          Robust Validation")
    print("=" * 60)

    repository_path = input(
        "\nEnter repository path:\n> "
    ).strip()

    try:

        result = validate_repository(
            repository_path
        )

        print("\n" + "=" * 60)
        print("              VALIDATION RESULT")
        print("=" * 60)

        print(
            f"\nProject type: "
            f"{result['project_type']}"
        )

        print(
            f"Status: "
            f"{result['status']}"
        )

        print(
            f"Success: "
            f"{result['success']}"
        )

        if result.get("reason"):

            print(
                f"\nReason:\n"
                f"{result['reason']}"
            )

        for index, validation in enumerate(
            result.get("results", []),
            start=1
        ):

            print(
                f"\nValidation {index}"
            )

            print(
                f"Command: "
                f"{' '.join(validation['command'])}"
            )

            print(
                f"Return code: "
                f"{validation['return_code']}"
            )

            print(
                f"Success: "
                f"{validation['success']}"
            )

            if validation["stdout"]:

                print(
                    f"\nOutput:\n"
                    f"{validation['stdout']}"
                )

            if validation["stderr"]:

                print(
                    f"\nError:\n"
                    f"{validation['stderr']}"
                )

    except Exception as error:

        print("\nERROR:")
        print(error)