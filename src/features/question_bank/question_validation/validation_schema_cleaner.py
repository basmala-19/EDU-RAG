from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import dirtyjson
from json_repair import loads as repair_json


INPUT_DIR = Path(
    r"F:\pythonProj\question_generator\llm_validation"
)

OUTPUT_DIR = Path(
    r"F:\pythonProj\question_generator\llm_validation\cleaned_json"
)


def clean_json_file(node_id: str) -> Path:
    """
    Read a JSON/JSON-like file from the llm_validation directory,
    repair/parse it using json-repair, and fall back to dirtyjson
    if json-repair fails.

    The cleaned result is written to the cleaned_json directory
    using exactly the same filename as the input file.

    Args:
        node_id:
            Input filename, with or without .json/.txt.
            Examples:
                "isometries.txt"
                "isometries.json"

    Returns:
        Path to the cleaned output file.

    Raises:
        TypeError:
            If node_id is not a string.

        ValueError:
            If node_id is empty or has an unsupported extension.

        FileNotFoundError:
            If the input file cannot be found.

        RuntimeError:
            If both json-repair and dirtyjson fail.
    """

    # ---------------------------------------------------------
    # Validate node_id
    # ---------------------------------------------------------

    if not isinstance(node_id, str):
        raise TypeError(
            "node_id must be a string."
        )

    node_id = node_id.strip()

    if not node_id:
        raise ValueError(
            "node_id cannot be empty."
        )

    # Prevent path traversal.
    filename = Path(node_id).name

    suffix = Path(filename).suffix.lower()

    if suffix not in {".json", ".txt"}:
        raise ValueError(
            f"Expected a .json or .txt file, got: '{filename}'"
        )

    # ---------------------------------------------------------
    # Locate input file
    # ---------------------------------------------------------

    input_path = INPUT_DIR / filename

    if not input_path.is_file():
        raise FileNotFoundError(
            f"Could not find input file:\n{input_path}"
        )

    # ---------------------------------------------------------
    # Read raw text
    # ---------------------------------------------------------

    try:
        raw_text = input_path.read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise OSError(
            f"Could not read '{input_path}': {exc}"
        ) from exc

    if not raw_text.strip():
        raise ValueError(
            f"Input file is empty: {input_path}"
        )

    # ---------------------------------------------------------
    # Try json-repair first
    # ---------------------------------------------------------

    parsed_data: Any = None
    parser_used: str | None = None
    repair_error: Exception | None = None

    try:
        parsed_data = repair_json(raw_text)
        parser_used = "json-repair"

    except Exception as exc:
        repair_error = exc

    # ---------------------------------------------------------
    # Fall back to dirtyjson
    # ---------------------------------------------------------

    if parsed_data is None:

        try:
            parsed_data = dirtyjson.loads(
                raw_text,
                search_for_first_object=True,
            )

            parsed_data = _convert_to_builtin(
                parsed_data
            )

            parser_used = "dirtyjson"

        except Exception as dirty_error:

            raise RuntimeError(
                "Could not parse/repair the input file "
                "with either json-repair or dirtyjson.\n\n"
                f"File: {input_path}\n\n"
                f"json-repair error:\n{repair_error}\n\n"
                f"dirtyjson error:\n{dirty_error}"
            ) from dirty_error

    # ---------------------------------------------------------
    # Ensure the result is valid JSON-serializable data
    # ---------------------------------------------------------

    try:
        # This also verifies that the parsed result can actually
        # be serialized as standard JSON.
        serialized = json.dumps(
            parsed_data,
            ensure_ascii=False,
            indent=2,
        )

    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"{parser_used} produced data that could not be "
            f"serialized as valid JSON for '{input_path}': {exc}"
        ) from exc

    # ---------------------------------------------------------
    # Create output directory
    # ---------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # Save using EXACT same filename
    # ---------------------------------------------------------

    output_path = OUTPUT_DIR / filename

    try:
        output_path.write_text(
            serialized + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise OSError(
            f"Could not write cleaned JSON to "
            f"'{output_path}': {exc}"
        ) from exc

    print(
        f"Cleaned '{filename}' using {parser_used}."
    )
    print(
        f"Saved to: {output_path}"
    )

    return output_path


def _convert_to_builtin(value: Any) -> Any:
    """
    Recursively convert dirtyjson's custom dict/list subclasses
    into ordinary Python dict/list objects.
    """

    if isinstance(value, dict):
        return {
            key: _convert_to_builtin(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _convert_to_builtin(item)
            for item in value
        ]

    return value


clean_json_file("isometries.txt")