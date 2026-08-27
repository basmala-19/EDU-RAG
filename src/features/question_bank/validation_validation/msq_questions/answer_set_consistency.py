from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ============================================================
# DIRECTORIES
# ============================================================

QUESTIONS_VALID_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\questions\valid"
)

VALIDATIONS_VALID_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\validations\valid"
)


# ============================================================
# FILE HELPERS
# ============================================================

def _normalize_node_id(node_id: str) -> str:
    """
    Normalize node_id into a safe filename stem.

    Examples:
        isometries
        isometries.json
        isometries.txt

    All become:
        isometries
    """

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
    node_id = Path(node_id).name

    return Path(node_id).stem


def _find_node_file(
    directory: Path,
    node_id: str,
) -> Path:
    """
    Find the file corresponding to node_id.

    .json is preferred, then .txt.
    """

    stem = _normalize_node_id(
        node_id
    )

    json_path = (
        directory
        / f"{stem}.json"
    )

    txt_path = (
        directory
        / f"{stem}.txt"
    )

    if json_path.is_file():
        return json_path

    if txt_path.is_file():
        return txt_path

    raise FileNotFoundError(
        f"Could not find file for node_id='{stem}' "
        f"in '{directory}'."
    )


def _load_json(
    path: Path,
) -> dict[str, Any]:
    """
    Load a JSON object from disk.
    """

    try:
        text = path.read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise OSError(
            f"Could not read '{path}': {exc}"
        ) from exc

    try:
        data = json.loads(
            text
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in '{path}': {exc}"
        ) from exc

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            f"Root of '{path}' must be a JSON object."
        )

    return data


def _save_json(
    path: Path,
    data: dict[str, Any],
) -> None:
    """
    Overwrite an existing JSON file with the adjusted data.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise OSError(
            f"Could not write '{path}': {exc}"
        ) from exc


# ============================================================
# MAIN FUNCTION
# ============================================================

def reconcile_answer_set_consistency(
    node_id: str,
) -> dict[str, Any]:
    """
    Reconcile the answer-set fields of an MSQ validation JSON
    against the authoritative original question JSON.

    Input:

        Questions:
            final_schemas/questions/valid/<node_id>

        Validation:
            final_schemas/validations/valid/<node_id>

    Only the validation JSON is modified.

    No questions are invalidated, removed, orphaned, or moved.

    For every question:

    1. Recompute the authoritative correct IDs from
       original.options[].correct.

    2. Ensure original.correct_option_ids is internally
       consistent with options[].correct.

    3. Set validation.provided_correct_option_ids to the
       authoritative original.correct_option_ids.

    4. Recompute verified_correct_option_ids from
       validation.option_validations[].independently_verified_correct.

    5. Set answer_correctness.valid according to whether
       verified_correct_option_ids exactly matches the original
       correct answer set.

    The updated validation JSON overwrites the existing validation
    file.

    Returns:
        The updated validation JSON as a Python dictionary.
    """

    stem = _normalize_node_id(
        node_id
    )

    # ========================================================
    # Locate files
    # ========================================================

    questions_path = _find_node_file(
        QUESTIONS_VALID_DIR,
        stem,
    )

    validation_path = _find_node_file(
        VALIDATIONS_VALID_DIR,
        stem,
    )

    # ========================================================
    # Load files
    # ========================================================

    questions_data = _load_json(
        questions_path
    )

    validation_data = _load_json(
        validation_path
    )

    questions = questions_data.get(
        "questions"
    )

    validation_questions = validation_data.get(
        "questions"
    )

    if not isinstance(
        questions,
        list,
    ):
        raise ValueError(
            f"'{questions_path}' must contain a "
            f"'questions' list."
        )

    if not isinstance(
        validation_questions,
        list,
    ):
        raise ValueError(
            f"'{validation_path}' must contain a "
            f"'questions' list."
        )

    # ========================================================
    # Build authoritative question map
    # ========================================================

    questions_by_id: dict[
        str,
        dict[str, Any]
    ] = {}

    for question_index, question in enumerate(
        questions
    ):

        if not isinstance(
            question,
            dict,
        ):
            raise ValueError(
                f"Original question {question_index} "
                f"is not an object."
            )

        question_id = question.get(
            "id"
        )

        if not isinstance(
            question_id,
            str,
        ):
            raise ValueError(
                f"Original question {question_index} "
                f"does not contain a valid string ID."
            )

        if question_id in questions_by_id:
            raise ValueError(
                f"Duplicate original question ID: "
                f"{question_id}"
            )

        questions_by_id[
            question_id
        ] = question

    # ========================================================
    # Statistics
    # ========================================================

    statistics = {
        "questions_checked": 0,
        "provided_correct_option_ids_fixed": 0,
        "verified_correct_option_ids_fixed": 0,
        "answer_correctness_valid_fixed": 0,
        "original_questions_with_inconsistent_answer_keys": 0,
        "option_validation_count_mismatches": 0,
        "questions_without_matching_original_question": 0,
    }

    # ========================================================
    # Process every validation question
    # ========================================================

    for validation_index, validation_question in enumerate(
        validation_questions
    ):

        statistics[
            "questions_checked"
        ] += 1

        if not isinstance(
            validation_question,
            dict,
        ):
            raise ValueError(
                f"Validation question {validation_index} "
                f"must be an object."
            )

        validation_id = validation_question.get(
            "id"
        )

        if not isinstance(
            validation_id,
            str,
        ):
            raise ValueError(
                f"Validation question {validation_index} "
                f"does not contain a valid string ID."
            )

        # ----------------------------------------------------
        # Match to authoritative original question
        # ----------------------------------------------------

        original_question = questions_by_id.get(
            validation_id
        )

        if original_question is None:

            statistics[
                "questions_without_matching_original_question"
            ] += 1

            # This function does NOT invalidate questions.
            # However, without an original question there is
            # no authoritative answer set to copy.
            #
            # Therefore we leave this validation question
            # untouched.
            continue

        # ----------------------------------------------------
        # Extract original options
        # ----------------------------------------------------

        original_options = original_question.get(
            "options"
        )

        if not isinstance(
            original_options,
            list,
        ):
            raise ValueError(
                f"Original question '{validation_id}' "
                f"does not contain a valid options list."
            )

        # ====================================================
        # 1. Compute source_correct_ids from options[].correct
        # ====================================================

        source_correct_ids = [
            option["id"]
            for option in original_options
            if (
                isinstance(
                    option,
                    dict,
                )
                and option.get("correct") is True
            )
        ]

        # ====================================================
        # 2. Check original.correct_option_ids
        # ====================================================

        original_correct_option_ids = (
            original_question.get(
                "correct_option_ids"
            )
        )

        if not isinstance(
            original_correct_option_ids,
            list,
        ):
            raise ValueError(
                f"Original question '{validation_id}' "
                f"has invalid 'correct_option_ids'."
            )

        # The original question itself should normally already
        # have been validated. We do NOT modify it here because
        # this pass is explicitly validation-schema-only.
        if (
            original_correct_option_ids
            != source_correct_ids
        ):

            statistics[
                "original_questions_with_inconsistent_answer_keys"
            ] += 1

        # ====================================================
        # AUTHORITATIVE SOURCE ANSWER SET
        #
        # options[].correct is the underlying source of truth.
        # ====================================================

        authoritative_correct_ids = list(
            source_correct_ids
        )

        # ====================================================
        # 3. provided_correct_option_ids
        # ====================================================

        answer_correctness = (
            validation_question.get(
                "answer_correctness"
            )
        )

        if not isinstance(
            answer_correctness,
            dict,
        ):
            raise ValueError(
                f"Validation question '{validation_id}' "
                f"does not contain a valid "
                f"'answer_correctness' object."
            )

        old_provided_ids = (
            answer_correctness.get(
                "provided_correct_option_ids"
            )
        )

        if (
            old_provided_ids
            != authoritative_correct_ids
        ):

            statistics[
                "provided_correct_option_ids_fixed"
            ] += 1

        # Make the validation copy exactly match
        # the authoritative source.
        answer_correctness[
            "provided_correct_option_ids"
        ] = list(
            authoritative_correct_ids
        )

        # ====================================================
        # 4. Recompute verified_correct_option_ids
        #    from option_validations
        # ====================================================

        option_validations = (
            answer_correctness.get(
                "option_validations"
            )
        )

        if not isinstance(
            option_validations,
            list,
        ):
            raise ValueError(
                f"Validation question '{validation_id}' "
                f"does not contain a valid "
                f"'option_validations' list."
            )

        # ----------------------------------------------------
        # We cannot manufacture independent judgments.
        #
        # We only aggregate the values the validator actually
        # supplied.
        # ----------------------------------------------------

        recomputed_verified_ids: list[str] = []

        for option_validation_index, option_validation in enumerate(
            option_validations
        ):

            if not isinstance(
                option_validation,
                dict,
            ):
                raise ValueError(
                    f"Question '{validation_id}': "
                    f"option validation {option_validation_index} "
                    f"must be an object."
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
                    f"Question '{validation_id}': "
                    f"option validation "
                    f"{option_validation_index} has invalid "
                    f"'independently_verified_correct'."
                )

            option_reference = (
                option_validation.get(
                    "option"
                )
            )

            if not isinstance(
                option_reference,
                dict,
            ):
                raise ValueError(
                    f"Question '{validation_id}': "
                    f"option validation "
                    f"{option_validation_index} has invalid "
                    f"'option' reference."
                )

            option_id = option_reference.get(
                "id"
            )

            if not isinstance(
                option_id,
                str,
            ):
                raise ValueError(
                    f"Question '{validation_id}': "
                    f"option validation "
                    f"{option_validation_index} has invalid "
                    f"option ID."
                )

            if independently_verified_correct:
                recomputed_verified_ids.append(
                    option_id
                )

        # ====================================================
        # 5. Verify current verified IDs
        # ====================================================

        old_verified_ids = (
            answer_correctness.get(
                "verified_correct_option_ids"
            )
        )

        if (
            old_verified_ids
            != recomputed_verified_ids
        ):

            statistics[
                "verified_correct_option_ids_fixed"
            ] += 1

        answer_correctness[
            "verified_correct_option_ids"
        ] = list(
            recomputed_verified_ids
        )

        # ====================================================
        # 6. Derive answer_correctness.valid
        # ====================================================

        expected_valid = (
            set(
                recomputed_verified_ids
            )
            ==
            set(
                authoritative_correct_ids
            )
        )

        old_valid = (
            answer_correctness.get(
                "valid"
            )
        )

        if old_valid != expected_valid:

            statistics[
                "answer_correctness_valid_fixed"
            ] += 1

        answer_correctness[
            "valid"
        ] = expected_valid

    # ========================================================
    # Save updated validation schema
    # ========================================================

    _save_json(
        validation_path,
        validation_data,
    )

    # ========================================================
    # Report
    # ========================================================

    print()
    print("=" * 72)
    print("ANSWER-SET CONSISTENCY RECONCILIATION COMPLETE")
    print("=" * 72)

    print(
        f"Node:                           {stem}"
    )

    print(
        f"Questions checked:              "
        f"{statistics['questions_checked']}"
    )

    print(
        f"provided_correct_option_ids "
        f"fixed:                         "
        f"{statistics['provided_correct_option_ids_fixed']}"
    )

    print(
        f"verified_correct_option_ids "
        f"fixed:                         "
        f"{statistics['verified_correct_option_ids_fixed']}"
    )

    print(
        f"answer_correctness.valid "
        f"fixed:                         "
        f"{statistics['answer_correctness_valid_fixed']}"
    )

    print(
        f"Original answer-key "
        f"inconsistencies:              "
        f"{statistics['original_questions_with_inconsistent_answer_keys']}"
    )

    print(
        f"Questions without original "
        f"match:                        "
        f"{statistics['questions_without_matching_original_question']}"
    )

    print()

    print(
        f"Updated validation file:"
    )
    print(
        f"  {validation_path}"
    )

    print("=" * 72)

    return validation_data


# ============================================================
# EXECUTION
# ============================================================

if __name__ == "__main__":

    reconcile_answer_set_consistency(
        node_id="isometries"
    )