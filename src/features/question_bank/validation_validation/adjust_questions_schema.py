from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ============================================================
# DIRECTORIES
# ============================================================

VALIDATION_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\validations\valid"
)

QUESTIONS_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\questions\valid"
)


# ============================================================
# HELPERS
# ============================================================

def _find_json_file(
    directory: Path,
    node_name: str,
) -> Path:
    """
    Find the JSON file corresponding to node_name.

    Accepts:
        "isometries"
        "isometries.json"

    Returns:
        Path to the JSON file.
    """

    if not isinstance(node_name, str):
        raise TypeError(
            "node_name must be a string."
        )

    node_name = node_name.strip()

    if not node_name:
        raise ValueError(
            "node_name cannot be empty."
        )

    # Prevent path traversal.
    filename = Path(node_name).name

    if Path(filename).suffix.lower() == ".json":
        candidates = [filename]
    else:
        candidates = [
            f"{filename}.json",
            filename,
        ]

    for candidate in candidates:

        path = directory / candidate

        if path.is_file():
            return path

    raise FileNotFoundError(
        f"Could not find JSON file for node_name='{node_name}'. "
        f"Directory: {directory}. "
        f"Searched for: {', '.join(candidates)}"
    )


def _load_json(
    path: Path,
) -> dict[str, Any]:
    """
    Load a JSON object from disk.
    """

    try:
        raw_text = path.read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise OSError(
            f"Could not read '{path}': {exc}"
        ) from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in '{path}': {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Root of '{path}' must be a JSON object."
        )

    return data


# ============================================================
# VALIDATION STRUCTURE CHECKS
# ============================================================

def _build_validation_index(
    validation_data: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Build:

        question_id -> validation question

    and perform consistency checks required for safe updating.
    """

    questions = validation_data.get(
        "questions"
    )

    if not isinstance(
        questions,
        list,
    ):
        raise ValueError(
            'Validation JSON must contain a "questions" array.'
        )

    index: dict[str, dict[str, Any]] = {}

    for question_index, validation_question in enumerate(
        questions
    ):

        if not isinstance(
            validation_question,
            dict,
        ):
            raise ValueError(
                f"Validation question {question_index} "
                "must be an object."
            )

        question_id = validation_question.get(
            "id"
        )

        if not isinstance(
            question_id,
            str,
        ) or not question_id.strip():
            raise ValueError(
                f"Validation question {question_index} "
                'has an invalid "id".'
            )

        if question_id in index:
            raise ValueError(
                f"Duplicate validation question ID: "
                f"'{question_id}'."
            )

        stem = validation_question.get(
            "stem"
        )

        if not isinstance(
            stem,
            str,
        ):
            raise ValueError(
                f"Validation question '{question_id}' "
                'has an invalid "stem".'
            )

        answer_correctness = validation_question.get(
            "answer_correctness"
        )

        if not isinstance(
            answer_correctness,
            dict,
        ):
            raise ValueError(
                f"Validation question '{question_id}' "
                'has no valid "answer_correctness" object.'
            )

        verified_ids = answer_correctness.get(
            "verified_correct_option_ids"
        )

        if not isinstance(
            verified_ids,
            list,
        ):
            raise ValueError(
                f"Validation question '{question_id}' "
                '"verified_correct_option_ids" must be a list.'
            )

        if not all(
            isinstance(option_id, str)
            for option_id in verified_ids
        ):
            raise ValueError(
                f"Validation question '{question_id}' "
                '"verified_correct_option_ids" must contain only strings.'
            )

        option_validations = answer_correctness.get(
            "option_validations"
        )

        if not isinstance(
            option_validations,
            list,
        ):
            raise ValueError(
                f"Validation question '{question_id}' "
                '"option_validations" must be a list.'
            )

        # ----------------------------------------------------
        # Cross-check verified IDs against option-level
        # independent determinations.
        # ----------------------------------------------------

        independently_verified_ids = []

        seen_option_ids: set[str] = set()

        for option_validation in option_validations:

            if not isinstance(
                option_validation,
                dict,
            ):
                raise ValueError(
                    f"Validation question '{question_id}' "
                    "contains a non-object option validation."
                )

            option_reference = option_validation.get(
                "option"
            )

            if not isinstance(
                option_reference,
                dict,
            ):
                raise ValueError(
                    f"Validation question '{question_id}' "
                    'has an option validation without "option".'
                )

            option_id = option_reference.get(
                "id"
            )

            if not isinstance(
                option_id,
                str,
            ) or not option_id.strip():
                raise ValueError(
                    f"Validation question '{question_id}' "
                    "contains an invalid option ID."
                )

            if option_id in seen_option_ids:
                raise ValueError(
                    f"Validation question '{question_id}' "
                    f"contains duplicate option ID '{option_id}'."
                )

            seen_option_ids.add(
                option_id
            )

            independently_verified_correct = (
                option_validation.get(
                    "independently_verified_correct"
                )
            )

            if not isinstance(
                independently_verified_correct,
                bool,
            ):
                raise ValueError(
                    f"Validation question '{question_id}', "
                    f"option '{option_id}': "
                    '"independently_verified_correct" '
                    "must be boolean."
                )

            if independently_verified_correct:
                independently_verified_ids.append(
                    option_id
                )

        # The validator's two representations of the
        # independently verified answer set must agree.
        if set(verified_ids) != set(
            independently_verified_ids
        ):
            raise ValueError(
                f"Validation question '{question_id}' is "
                "internally inconsistent:\n"
                f"verified_correct_option_ids = "
                f"{sorted(verified_ids)}\n"
                f"option-level independently verified IDs = "
                f"{sorted(independently_verified_ids)}"
            )

        # ----------------------------------------------------
        # The top-level valid field must agree with the
        # validated answer sets.
        # ----------------------------------------------------

        valid = answer_correctness.get(
            "valid"
        )

        provided_ids = answer_correctness.get(
            "provided_correct_option_ids"
        )

        if not isinstance(
            valid,
            bool,
        ):
            raise ValueError(
                f"Validation question '{question_id}' "
                '"answer_correctness.valid" must be boolean.'
            )

        if not isinstance(
            provided_ids,
            list,
        ) or not all(
            isinstance(option_id, str)
            for option_id in provided_ids
        ):
            raise ValueError(
                f"Validation question '{question_id}' "
                '"provided_correct_option_ids" must be a '
                "list of strings."
            )

        expected_valid = (
            set(verified_ids)
            == set(provided_ids)
        )

        if valid != expected_valid:
            raise ValueError(
                f"Validation question '{question_id}' is "
                "internally inconsistent:\n"
                f'"valid" = {valid}, but the verified and '
                f"provided answer sets imply {expected_valid}."
            )

        index[question_id] = validation_question

    return index


# ============================================================
# MAIN FUNCTION
# ============================================================

def update_questions_from_validation(
    node_name: str,
) -> Path:
    """
    Reconcile the generated questions JSON against its validated
    version and update the original questions in-place.

    Authoritative source for corrections:
        validation.answer_correctness.option_validations[
            ...
        ].independently_verified_correct

    For every question:

        - If an option's `correct` value is wrong, correct it.
        - Rebuild `correct_option_ids` from the validated answer set.
        - Add `"modified": true` if anything changed.
        - Add `"modified": false` otherwise.

    The questions JSON is updated in-place.

    Args:
        node_name:
            File name identifying the questions and validation JSONs.

    Returns:
        Path to the updated questions JSON.
    """

    # ========================================================
    # 1. Locate files
    # ========================================================

    validation_path = _find_json_file(
        VALIDATION_DIR,
        node_name,
    )

    questions_path = _find_json_file(
        QUESTIONS_DIR,
        node_name,
    )

    # ========================================================
    # 2. Load files
    # ========================================================

    validation_data = _load_json(
        validation_path
    )

    questions_data = _load_json(
        questions_path
    )

    # ========================================================
    # 3. Build validation index
    # ========================================================

    validation_index = _build_validation_index(
        validation_data
    )

    # ========================================================
    # 4. Validate questions root
    # ========================================================

    questions = questions_data.get(
        "questions"
    )

    if not isinstance(
        questions,
        list,
    ):
        raise ValueError(
            f"Questions JSON must contain a "
            f'"questions" array: {questions_path}'
        )

    # ========================================================
    # 5. Ensure question IDs are unique
    # ========================================================

    question_ids: set[str] = set()

    for question_index, question in enumerate(
        questions
    ):

        if not isinstance(
            question,
            dict,
        ):
            raise ValueError(
                f"Question {question_index} must be an object."
            )

        question_id = question.get(
            "id"
        )

        if not isinstance(
            question_id,
            str,
        ) or not question_id.strip():
            raise ValueError(
                f"Question {question_index} has an invalid "
                '"id".'
            )

        if question_id in question_ids:
            raise ValueError(
                f"Duplicate question ID '{question_id}' "
                f"in questions file."
            )

        question_ids.add(
            question_id
        )

    # ========================================================
    # 6. Process every generated question
    # ========================================================

    modified_count = 0
    unchanged_count = 0

    for question_index, question in enumerate(
        questions
    ):

        question_id = question[
            "id"
        ]

        # ----------------------------------------------------
        # A question without a validation result cannot safely
        # be modified.
        # ----------------------------------------------------

        validation_question = validation_index.get(
            question_id
        )

        if validation_question is None:
            raise ValueError(
                f"Question '{question_id}' has no corresponding "
                "validation result."
            )

        # ----------------------------------------------------
        # Verify stems correspond.
        # ----------------------------------------------------

        question_stem = question.get(
            "stem"
        )

        validation_stem = validation_question.get(
            "stem"
        )

        if question_stem != validation_stem:
            raise ValueError(
                f"Stem mismatch for question '{question_id}'.\n"
                f"Questions file stem:\n"
                f"{question_stem!r}\n\n"
                f"Validation stem:\n"
                f"{validation_stem!r}"
            )

        # ----------------------------------------------------
        # Retrieve validation answer data.
        # ----------------------------------------------------

        answer_correctness = validation_question[
            "answer_correctness"
        ]

        option_validations = answer_correctness[
            "option_validations"
        ]

        verified_correct_option_ids = (
            answer_correctness[
                "verified_correct_option_ids"
            ]
        )

        # ----------------------------------------------------
        # Index validation options by option ID.
        # ----------------------------------------------------

        validation_options_by_id: dict[
            str,
            dict[str, Any]
        ] = {}

        for option_validation in option_validations:

            option = option_validation[
                "option"
            ]

            option_id = option[
                "id"
            ]

            validation_options_by_id[
                option_id
            ] = option_validation

        # ----------------------------------------------------
        # Validate that every original option is represented.
        # ----------------------------------------------------

        original_options = question.get(
            "options"
        )

        if not isinstance(
            original_options,
            list,
        ):
            raise ValueError(
                f"Question '{question_id}' has no valid "
                '"options" list.'
            )

        original_option_ids = [
            option.get("id")
            for option in original_options
            if isinstance(option, dict)
        ]

        if len(original_option_ids) != len(
            original_options
        ):
            raise ValueError(
                f"Question '{question_id}' contains "
                "an invalid option object."
            )

        if set(validation_options_by_id) != set(
            original_option_ids
        ):
            raise ValueError(
                f"Option mismatch for question "
                f"'{question_id}'.\n"
                f"Original option IDs: "
                f"{sorted(original_option_ids)}\n"
                f"Validation option IDs: "
                f"{sorted(validation_options_by_id)}"
            )

        # ====================================================
        # Determine modifications
        # ====================================================

        question_modified = False

        # ----------------------------------------------------
        # 6A. Correct each option's `correct` field
        # ----------------------------------------------------

        for option in original_options:

            option_id = option[
                "id"
            ]

            validation_option = (
                validation_options_by_id[
                    option_id
                ]
            )

            independently_verified_correct = (
                validation_option[
                    "independently_verified_correct"
                ]
            )

            original_correct = option[
                "correct"
            ]

            if (
                original_correct
                != independently_verified_correct
            ):

                option[
                    "correct"
                ] = independently_verified_correct

                question_modified = True

        # ----------------------------------------------------
        # 6B. Rebuild correct_option_ids
        #
        # Preserve the order of the question's options.
        # ----------------------------------------------------

        expected_correct_option_ids = [
            option[
                "id"
            ]
            for option in original_options
            if option[
                "correct"
            ] is True
        ]

        # The reconstructed set should agree with the
        # validation result.
        if set(expected_correct_option_ids) != set(
            verified_correct_option_ids
        ):
            raise ValueError(
                f"Validation inconsistency for question "
                f"'{question_id}': after applying "
                "independently_verified_correct, the "
                "correct-option set does not match "
                "verified_correct_option_ids.\n"
                f"Computed: {expected_correct_option_ids}\n"
                f"Validated: {verified_correct_option_ids}"
            )

        if question[
            "correct_option_ids"
        ] != expected_correct_option_ids:

            question[
                "correct_option_ids"
            ] = expected_correct_option_ids

            question_modified = True

        # ----------------------------------------------------
        # 6C. Set modified flag
        # ----------------------------------------------------

        if question_modified:

            question[
                "modified"
            ] = True

            modified_count += 1

        else:

            question[
                "modified"
            ] = False

            unchanged_count += 1

    # ========================================================
    # 7. Save updated questions file IN PLACE
    # ========================================================

    try:
        questions_path.write_text(
            json.dumps(
                questions_data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise OSError(
            f"Could not write updated questions file "
            f"'{questions_path}': {exc}"
        ) from exc

    # ========================================================
    # 8. Report
    # ========================================================

    print(
        "=" * 72
    )
    print(
        "QUESTION VALIDATION RECONCILIATION COMPLETE"
    )
    print(
        "=" * 72
    )

    print(
        f"Node:              "
        f"{Path(node_name).stem}"
    )

    print(
        f"Questions file:    "
        f"{questions_path}"
    )

    print(
        f"Validation file:   "
        f"{validation_path}"
    )

    print(
        f"Total questions:   "
        f"{len(questions)}"
    )

    print(
        f"Modified:          "
        f"{modified_count}"
    )

    print(
        f"Unchanged:         "
        f"{unchanged_count}"
    )

    print(
        f"Updated file:      "
        f"{questions_path}"
    )

    print(
        "=" * 72
    )

    return questions_path


# ============================================================
# EXAMPLE
# ============================================================

if __name__ == "__main__":

    update_questions_from_validation(
        node_name="isometries"
    )