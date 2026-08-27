from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import dirtyjson
from json_repair import loads as repair_json


# =============================================================
# CONFIGURATION
# =============================================================

OUTPUT_DIR = Path(
    r"F:\pythonProj\question_generator\llm_response_generations\jsons_with_ids"
)

PROBLEMATIC_DIR = Path(
    r"F:\pythonProj\question_generator\llm_response_generations\problematic_json"
)


# =============================================================
# JSON EXTRACTION / REPAIR
# =============================================================

def extract_json_from_text(
    text: str,
) -> dict[str, Any]:
    """
    Parse LLM-generated question JSON.

    Parsing strategy:
        1. json-repair
        2. dirtyjson fallback if json-repair cannot parse
        3. Root-level validation

    Question-level validation is intentionally NOT performed here.
    Each question is validated independently later.

    Expected root structure:

        {
            "questions": [...]
        }
    """

    # =========================================================
    # 1. Primary parser: json-repair
    # =========================================================

    try:
        data = repair_json(text)

    except Exception as repair_exc:

        # =====================================================
        # 2. Fallback parser: dirtyjson
        # =====================================================

        try:
            data = dirtyjson.loads(
                text,
                search_for_first_object=True,
            )

            data = _convert_dirtyjson_to_builtin(
                data
            )

        except Exception as dirty_exc:

            raise ValueError(
                "Unable to parse LLM output with either parser.\n"
                f"json-repair error: {repair_exc}\n"
                f"dirtyjson error: {dirty_exc}"
            ) from dirty_exc

    # =========================================================
    # 3. Root validation
    # =========================================================

    if not isinstance(data, dict):
        raise ValueError(
            "Root JSON must be an object."
        )

    questions = data.get(
        "questions"
    )

    if not isinstance(
        questions,
        list,
    ):
        raise ValueError(
            'Root JSON must contain "questions" as a list.'
        )

    if not questions:
        raise ValueError(
            '"questions" must contain at least one question.'
        )

    return data


def _convert_dirtyjson_to_builtin(
    value: Any,
) -> Any:
    """
    Convert dirtyjson AttributedDict / AttributedList objects
    recursively into ordinary Python dict/list objects.
    """

    if isinstance(value, dict):
        return {
            key: _convert_dirtyjson_to_builtin(
                item
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _convert_dirtyjson_to_builtin(
                item
            )
            for item in value
        ]

    return value


# =============================================================
# QUESTION VALIDATION
# =============================================================

def _validate_question(
    question: Any,
    question_index: int,
) -> list[str]:
    """
    Validate ONE question structurally.

    IMPORTANT:

    This function intentionally does NOT reject a question when
    `correct_option_ids` disagrees with the individual option
    `correct` values.

    That inconsistency is allowed to pass through this stage
    because it will be independently validated and corrected
    later by the question-validation pipeline.

    Returns:
        A list of validation errors.

    An empty list means the question is structurally valid.
    """

    errors: list[str] = []

    # ---------------------------------------------------------
    # Question must be an object
    # ---------------------------------------------------------

    if not isinstance(
        question,
        dict,
    ):
        return [
            f"Question {question_index} is not an object."
        ]

    # ---------------------------------------------------------
    # question_type
    # ---------------------------------------------------------

    if question.get(
        "question_type"
    ) != "MSQ":

        errors.append(
            f'Question {question_index}: '
            '"question_type" must be "MSQ".'
        )

    # ---------------------------------------------------------
    # stem
    # ---------------------------------------------------------

    stem = question.get(
        "stem"
    )

    if (
        not isinstance(
            stem,
            str,
        )
        or not stem.strip()
    ):

        errors.append(
            f'Question {question_index}: '
            '"stem" must be a non-empty string.'
        )

    # ---------------------------------------------------------
    # options
    # ---------------------------------------------------------

    options = question.get(
        "options"
    )

    if not isinstance(
        options,
        list,
    ):

        errors.append(
            f'Question {question_index}: '
            '"options" must be a list.'
        )

        options = []

    elif len(options) < 4:

        errors.append(
            f'Question {question_index}: '
            '"options" must contain at least 4 items.'
        )

    option_ids: set[str] = set()

    for option_index, option in enumerate(
        options
    ):

        if not isinstance(
            option,
            dict,
        ):

            errors.append(
                f"Question {question_index}, "
                f"option {option_index}: "
                "must be an object."
            )

            continue

        # -----------------------------------------------------
        # option.id
        # -----------------------------------------------------

        option_id = option.get(
            "id"
        )

        if (
            not isinstance(
                option_id,
                str,
            )
            or not option_id.strip()
        ):

            errors.append(
                f"Question {question_index}, "
                f"option {option_index}: "
                '"id" must be a non-empty string.'
            )

        else:

            if option_id in option_ids:

                errors.append(
                    f"Question {question_index}: "
                    f'duplicate option ID "{option_id}".'
                )

            option_ids.add(
                option_id
            )

        # -----------------------------------------------------
        # option.text
        # -----------------------------------------------------

        option_text = option.get(
            "text"
        )

        if (
            not isinstance(
                option_text,
                str,
            )
            or not option_text.strip()
        ):

            errors.append(
                f"Question {question_index}, "
                f'option "{option_id}": '
                '"text" must be a non-empty string.'
            )

        # -----------------------------------------------------
        # option.correct
        # -----------------------------------------------------

        if not isinstance(
            option.get("correct"),
            bool,
        ):

            errors.append(
                f"Question {question_index}, "
                f'option "{option_id}": '
                '"correct" must be a boolean.'
            )

        # -----------------------------------------------------
        # option.justification
        # -----------------------------------------------------

        justification = option.get(
            "justification"
        )

        if (
            not isinstance(
                justification,
                str,
            )
            or not justification.strip()
        ):

            errors.append(
                f"Question {question_index}, "
                f'option "{option_id}": '
                '"justification" must be a non-empty string.'
            )

    # ---------------------------------------------------------
    # correct_option_ids
    # ---------------------------------------------------------

    correct_option_ids = question.get(
        "correct_option_ids"
    )

    if not isinstance(
        correct_option_ids,
        list,
    ):

        errors.append(
            f'Question {question_index}: '
            '"correct_option_ids" must be a list.'
        )

        correct_option_ids = []

    elif not correct_option_ids:

        errors.append(
            f'Question {question_index}: '
            '"correct_option_ids" cannot be empty.'
        )

    # ---------------------------------------------------------
    # All correct IDs must be strings
    # ---------------------------------------------------------

    if not all(
        isinstance(option_id, str)
        for option_id in correct_option_ids
    ):

        errors.append(
            f'Question {question_index}: '
            '"correct_option_ids" must contain only strings.'
        )

    # ---------------------------------------------------------
    # Duplicate correct IDs
    # ---------------------------------------------------------

    if len(correct_option_ids) != len(
        set(correct_option_ids)
    ):

        errors.append(
            f'Question {question_index}: '
            '"correct_option_ids" contains duplicates.'
        )

    # ---------------------------------------------------------
    # Unknown correct IDs
    # ---------------------------------------------------------

    unknown_ids = (
        set(correct_option_ids)
        - option_ids
    )

    if unknown_ids:

        errors.append(
            f'Question {question_index}: '
            '"correct_option_ids" contains unknown IDs: '
            f"{sorted(unknown_ids)}"
        )

    # =========================================================
    # IMPORTANT:
    #
    # DO NOT reject the question if:
    #
    #     option["correct"] values
    #
    # disagree with:
    #
    #     correct_option_ids
    #
    # This is intentionally deferred to the validation pipeline.
    # =========================================================

    # ---------------------------------------------------------
    # bloom_level
    # ---------------------------------------------------------

    valid_bloom_levels = {
        "remember",
        "understand",
        "apply",
        "analyze",
        "evaluate",
        "create",
    }

    bloom_level = question.get(
        "bloom_level"
    )

    if bloom_level not in valid_bloom_levels:

        errors.append(
            f'Question {question_index}: '
            f'"bloom_level" must be one of '
            f"{sorted(valid_bloom_levels)}."
        )

    # ---------------------------------------------------------
    # task_difficulty
    # ---------------------------------------------------------

    task_difficulty = question.get(
        "task_difficulty"
    )

    if (
        not isinstance(
            task_difficulty,
            int,
        )
        or isinstance(
            task_difficulty,
            bool,
        )
        or not 1 <= task_difficulty <= 5
    ):

        errors.append(
            f'Question {question_index}: '
            '"task_difficulty" must be an integer from 1 to 5.'
        )

    # ---------------------------------------------------------
    # msq_difficulty
    # ---------------------------------------------------------

    msq_difficulty = question.get(
        "msq_difficulty"
    )

    if (
        not isinstance(
            msq_difficulty,
            int,
        )
        or isinstance(
            msq_difficulty,
            bool,
        )
        or not 1 <= msq_difficulty <= 3
    ):

        errors.append(
            f'Question {question_index}: '
            '"msq_difficulty" must be an integer from 1 to 3.'
        )

    return errors


# =============================================================
# CANONICAL JSON
# =============================================================

def _canonical_json(
    value: Any,
) -> str:
    """
    Create a deterministic JSON representation.

    Dictionary key order and insignificant whitespace do not
    affect the resulting string.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


# =============================================================
# QUESTION ID
# =============================================================

def _generate_question_id(
    question: dict[str, Any],
) -> str:
    """
    Generate a deterministic ID representing the question itself.

    For a structurally valid question, identity is based on:

        - question_type
        - stem
        - option IDs
        - option text
        - option correctness

    Metadata such as justification, Bloom level and difficulty
    does not affect identity.

    If the question is malformed and some of those fields are
    missing, a fallback identity is generated from the available
    question content.
    """

    # ---------------------------------------------------------
    # Preferred semantic identity
    # ---------------------------------------------------------

    if (
        isinstance(
            question.get("question_type"),
            str,
        )
        and isinstance(
            question.get("stem"),
            str,
        )
        and isinstance(
            question.get("options"),
            list,
        )
    ):

        normalized_options = []

        for option in question[
            "options"
        ]:

            if not isinstance(
                option,
                dict,
            ):

                normalized_options.append(
                    option
                )

                continue

            normalized_options.append(
                {
                    "id": option.get("id"),
                    "text": option.get("text"),
                    "correct": option.get("correct"),
                }
            )

        identity = {
            "question_type": question.get(
                "question_type"
            ),
            "stem": question.get(
                "stem"
            ),
            "options": normalized_options,
            "correct_option_ids": question.get(
                "correct_option_ids"
            ),
        }

    else:

        # -----------------------------------------------------
        # Fallback identity for severely malformed questions.
        # -----------------------------------------------------

        identity = {
            key: value
            for key, value in question.items()
            if key != "id"
        }

    canonical = _canonical_json(
        identity
    )

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    # 128 bits retained from SHA-256.
    return f"q_{digest[:32]}"


# =============================================================
# SAVE PROBLEMATIC REASONS
# =============================================================

def _save_problematic_reasons(
    input_path: Path,
    problematic_reasons: list[tuple[str, list[str]]],
) -> Path | None:
    """
    Save reasons for problematic questions.

    Output filename:

        <input_stem>_reasons.json

    Example:

        isometries_reasons.json

    JSON does not have a native tuple type, so each tuple is
    represented as a two-element JSON array:

        [
            [
                "q_123...",
                [
                    "Reason 1",
                    "Reason 2"
                ]
            ]
        ]

    Returns:
        Path to the reasons file, or None if there are no
        problematic questions.
    """

    if not problematic_reasons:
        return None

    PROBLEMATIC_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    reasons_path = (
        PROBLEMATIC_DIR
        / f"{input_path.stem}_reasons.json"
    )

    # Convert tuples into JSON-compatible lists.
    serializable_reasons = [
        [
            question_id,
            reasons,
        ]
        for question_id, reasons in problematic_reasons
    ]

    try:
        with reasons_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                serializable_reasons,
                file,
                ensure_ascii=False,
                indent=2,
            )

            file.write("\n")

    except OSError as exc:

        raise OSError(
            f"Could not save problematic-question reasons "
            f"to '{reasons_path}': {exc}"
        ) from exc

    return reasons_path


# =============================================================
# MAIN FUNCTION
# =============================================================

def add_question_ids(
    file_path: str | Path,
) -> tuple[Path, Path | None]:

    input_path = Path(
        file_path
    )

    # ---------------------------------------------------------
    # Validate input path
    # ---------------------------------------------------------

    if not input_path.exists():

        raise FileNotFoundError(
            f"Input file does not exist: {input_path}"
        )

    if not input_path.is_file():

        raise ValueError(
            f"Path is not a file: {input_path}"
        )

    if input_path.suffix.lower() not in {
        ".json",
        ".txt",
    }:

        raise ValueError(
            f"Expected a .json or .txt file, "
            f"got: {input_path}"
        )

    # ---------------------------------------------------------
    # Read raw LLM response
    # ---------------------------------------------------------

    try:

        raw_text = input_path.read_text(
            encoding="utf-8"
        )

    except OSError as exc:

        raise ValueError(
            f"Could not read '{input_path}': {exc}"
        ) from exc

    if not raw_text.strip():

        raise ValueError(
            f"Input file is empty: {input_path}"
        )

    # ---------------------------------------------------------
    # Parse / repair JSON
    # ---------------------------------------------------------

    try:

        data = extract_json_from_text(
            raw_text
        )

    except ValueError as exc:

        PROBLEMATIC_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        problematic_path = (
            PROBLEMATIC_DIR
            / input_path.name
        )

        problematic_path.write_text(
            raw_text,
            encoding="utf-8",
        )

        raise ValueError(
            "Could not parse the input file.\n"
            f"Raw problematic response saved to:\n"
            f"{problematic_path}\n\n"
            f"Reason:\n{exc}"
        ) from exc

    # ---------------------------------------------------------
    # Separate valid and problematic questions
    # ---------------------------------------------------------

    valid_questions: list[
        dict[str, Any]
    ] = []

    problematic_questions: list[
        Any
    ] = []

    # This retains the reason for EVERY problematic question.
    #
    # Each entry will eventually be:
    #
    # (
    #     question_id,
    #     [
    #         "reason 1",
    #         "reason 2"
    #     ]
    # )
    #
    problematic_reasons_by_index: dict[
        int,
        list[str],
    ] = {}

    for question_index, question in enumerate(
        data["questions"]
    ):

        errors = _validate_question(
            question,
            question_index,
        )

        if errors:

            problematic_questions.append(
                question
            )

            problematic_reasons_by_index[
                question_index
            ] = errors

        else:

            assert isinstance(
                question,
                dict,
            )

            valid_questions.append(
                question
            )

    # ---------------------------------------------------------
    # Generate IDs for valid questions
    # and detect duplicate question identities
    # ---------------------------------------------------------

    unique_valid_questions: list[
        dict[str, Any]
    ] = []

    seen_ids: dict[
        str,
        int,
    ] = {}

    # Maps the original index of a valid question to its
    # generated ID.
    valid_question_index_to_id: dict[
        int,
        str,
    ] = {}

    for original_index, question in enumerate(
        valid_questions
    ):

        question_id = _generate_question_id(
            question
        )

        if question_id in seen_ids:

            problematic_questions.append(
                question
            )

            duplicate_reason = [
                "Duplicate question identity.",
                f"Generated ID: {question_id}.",
                "The same question identity already "
                f"occurred at question index "
                f"{seen_ids[question_id]}.",
            ]

            # The index here is the index within valid_questions,
            # which is sufficient for the reason record.
            problematic_reasons_by_index[
                original_index
            ] = duplicate_reason

            # Assign the ID before saving the problematic question.
            question[
                "id"
            ] = question_id

            continue

        seen_ids[
            question_id
        ] = original_index

        question[
            "id"
        ] = question_id

        valid_question_index_to_id[
            original_index
        ] = question_id

        unique_valid_questions.append(
            question
        )

    valid_questions = (
        unique_valid_questions
    )

    # ---------------------------------------------------------
    # Generate IDs for structurally problematic questions
    # ---------------------------------------------------------

    #
    # Important:
    #
    # `problematic_questions` contains objects from the original
    # list. We need to associate each question with its reason.
    #
    # The original validation errors are currently indexed by
    # original question position. Therefore we reconstruct the
    # reason information while processing the problematic list.
    #

    problematic_reasons: list[
        tuple[str, list[str]]
    ] = []

    #
    # The simplest reliable mechanism is to validate each
    # problematic question again against the ORIGINAL list
    # position and combine the generated ID with the errors.
    #

    problematic_id_set: set[int] = set()

    for question_index, question in enumerate(
        data["questions"]
    ):

        errors = _validate_question(
            question,
            question_index,
        )

        if not errors:
            continue

        if not isinstance(
            question,
            dict,
        ):
            #
            # Non-dictionary questions cannot receive a
            # question-level deterministic ID.
            #
            # We still preserve a useful identifier so that
            # the reason is not lost.
            #
            problematic_id = (
                f"invalid_index_{question_index:04d}"
            )

        else:

            problematic_id = _generate_question_id(
                question
            )

            question[
                "id"
            ] = problematic_id

        problematic_reasons.append(
            (
                problematic_id,
                errors,
            )
        )

        problematic_id_set.add(
            id(question)
        )

    # ---------------------------------------------------------
    # Add duplicate-identity reasons
    # ---------------------------------------------------------

    #
    # Duplicate questions were not caught by structural
    # validation. They are added to problematic_questions above.
    #
    # Add their reasons explicitly.
    #

    for original_index, question in enumerate(
        valid_questions
    ):
        #
        # At this point duplicate questions have already been
        # removed, so nothing is needed here.
        #
        pass

    #
    # The duplicate questions need to be represented in the
    # reasons list as well. We reconstruct them from the original
    # data by finding repeated generated IDs.
    #

    all_question_ids: dict[
        str,
        int,
    ] = {}

    for original_index, question in enumerate(
        data["questions"]
    ):

        if not isinstance(
            question,
            dict,
        ):
            continue

        question_id = _generate_question_id(
            question
        )

        if question_id not in all_question_ids:

            all_question_ids[
                question_id
            ] = original_index

            continue

        first_index = all_question_ids[
            question_id
        ]

        #
        # Only add a duplicate reason if this question is
        # actually present in problematic_questions.
        #
        # Structurally invalid questions can also have repeated
        # identities, so duplicates are only supplementary
        # information.
        #

        duplicate_question_is_problematic = (
            question in problematic_questions
        )

        if duplicate_question_is_problematic:

            duplicate_reason = [
                "Duplicate question identity.",
                f"Generated ID: {question_id}.",
                f"First occurrence was question "
                f"index {first_index}.",
            ]

            # Avoid adding an exact duplicate reason twice.
            existing = False

            for existing_id, existing_reasons in (
                problematic_reasons
            ):

                if (
                    existing_id == question_id
                    and existing_reasons
                    == duplicate_reason
                ):

                    existing = True
                    break

            if not existing:

                problematic_reasons.append(
                    (
                        question_id,
                        duplicate_reason,
                    )
                )

    # ---------------------------------------------------------
    # Save valid questions
    # ---------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / input_path.name
    )

    valid_data = {
        "questions": valid_questions
    }

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            valid_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")

    # ---------------------------------------------------------
    # Save problematic questions
    # ---------------------------------------------------------

    problematic_output_path: Path | None = None

    if problematic_questions:

        PROBLEMATIC_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        problematic_output_path = (
            PROBLEMATIC_DIR
            / input_path.name
        )

        problematic_data = {
            "questions": problematic_questions
        }

        with problematic_output_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                problematic_data,
                file,
                ensure_ascii=False,
                indent=2,
            )

            file.write("\n")

    # ---------------------------------------------------------
    # Save problematic reasons
    # ---------------------------------------------------------

    reasons_output_path = (
        _save_problematic_reasons(
            input_path=input_path,
            problematic_reasons=problematic_reasons,
        )
    )

    # ---------------------------------------------------------
    # Console report
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("QUESTION PROCESSING COMPLETE")
    print("=" * 70)

    print(
        f"Input file:            {input_path}"
    )

    print(
        f"Total questions:       "
        f"{len(data['questions'])}"
    )

    print(
        f"Valid questions:       "
        f"{len(valid_questions)}"
    )

    print(
        f"Problematic questions: "
        f"{len(problematic_questions)}"
    )

    print()

    print(
        f"Valid output:          "
        f"{output_path}"
    )

    if problematic_output_path is not None:

        print(
            f"Problematic output:    "
            f"{problematic_output_path}"
        )

    if reasons_output_path is not None:

        print(
            f"Problem reasons:      "
            f"{reasons_output_path}"
        )

    else:

        print(
            "No problematic-question reasons file "
            "was created because there were no problematic questions."
        )

    print()

    if problematic_reasons:

        print("-" * 70)
        print("PROBLEMATIC QUESTION REASONS")
        print("-" * 70)

        for question_id, reasons in (
            problematic_reasons
        ):

            print()
            print(
                f"Question ID: {question_id}"
            )

            for reason in reasons:

                print(
                    f"  - {reason}"
                )

    else:

        print(
            "No problematic questions."
        )

    print("=" * 70)

    return (
        output_path,
        problematic_output_path,
    )


# =============================================================
# EXECUTION
# =============================================================

if __name__ == "__main__":

    add_question_ids(
        r"F:\pythonProj\question_generator\llm_response_generations\isometries.txt"
    )