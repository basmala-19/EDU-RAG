from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


# ============================================================
# DIRECTORIES
# ============================================================

QUESTIONS_VALID_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\questions\valid"
)

QUESTIONS_ORPHAN_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\questions\orphan"
)

VALIDATIONS_VALID_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\validations\valid"
)

VALIDATIONS_INVALID_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\validations\invalid"
)

VALIDATIONS_METADATA_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\validations"
)


# ============================================================
# CONFIGURATION
# ============================================================

OPTION_TEXT_SIMILARITY_THRESHOLD = 0.90


# ============================================================
# FILE HELPERS
# ============================================================

def _safe_node_id(node_id: str) -> str:
    """
    Normalize node_id to a filename stem.

    Examples:
        isometries       -> isometries
        isometries.json  -> isometries
        isometries.txt   -> isometries
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


def _find_json_file(
    directory: Path,
    node_id: str,
) -> Path:
    """
    Find a file corresponding to node_id.

    .json is preferred, but .txt is supported.
    """

    stem = _safe_node_id(node_id)

    candidates = [
        directory / f"{stem}.json",
        directory / f"{stem}.txt",
    ]

    for path in candidates:
        if path.is_file():
            return path

    raise FileNotFoundError(
        f"Could not find '{stem}' in '{directory}'. "
        f"Searched for: "
        f"{', '.join(path.name for path in candidates)}"
    )


def _load_json_file(
    path: Path,
) -> dict[str, Any]:
    """
    Load a JSON object from disk.
    """

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except OSError as exc:
        raise OSError(
            f"Could not read '{path}': {exc}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in '{path}': {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Root of '{path}' must be a JSON object."
        )

    return data


def _save_json_file(
    path: Path,
    data: dict[str, Any],
) -> None:
    """
    Save a JSON object.
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
            ) + "\n",
            encoding="utf-8",
        )

    except OSError as exc:
        raise OSError(
            f"Could not write '{path}': {exc}"
        ) from exc


# ============================================================
# TEXT NORMALIZATION / SIMILARITY
# ============================================================

def _normalize_option_text(
    text: str,
) -> str:
    """
    Normalize option text for tolerant comparison.
    """

    if not isinstance(text, str):
        return ""

    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    text = text.casefold()

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2212": "-",
        "\u2013": "-",
        "\u2014": "-",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new,
        )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _option_text_similarity(
    text_a: str,
    text_b: str,
) -> float:
    """
    Return similarity in [0, 1].
    """

    a = _normalize_option_text(
        text_a
    )

    b = _normalize_option_text(
        text_b
    )

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


# ============================================================
# APPEND-ONLY ARCHIVE HELPERS
# ============================================================

def _append_questions_to_archive(
    path: Path,
    questions: list[dict[str, Any]],
) -> None:
    """
    Append questions to an existing archive without overwriting
    previous contents.
    """

    if not questions:
        return

    if path.exists():

        existing = _load_json_file(
            path
        )

        existing_questions = existing.get(
            "questions"
        )

        if not isinstance(
            existing_questions,
            list,
        ):
            raise ValueError(
                f"'{path}' does not contain a valid "
                f"'questions' list."
            )

    else:

        existing = {
            "questions": []
        }

        existing_questions = existing[
            "questions"
        ]

    existing_questions.extend(
        questions
    )

    _save_json_file(
        path,
        existing,
    )


# ============================================================
# MODIFICATION TRACKING
# ============================================================

def _record_question_modification(
    question: dict[str, Any],
    reason: str,
) -> None:
    """
    Persistently mark a question as modified.

    Rules:

        missing modified
            -> create it

        modified == False
            -> True when a modification occurs

        modified == True
            -> remains True forever

        missing reason
            -> create reason

        reason == None
            -> replace with new reason

        existing reason string
            -> append new reason

    A modification reason is appended only when an actual
    modification occurred.
    """

    # --------------------------------------------------------
    # modified
    # --------------------------------------------------------

    existing_modified = question.get(
        "modified"
    )

    if existing_modified is not True:
        question["modified"] = True
    else:
        # Explicitly preserve True.
        question["modified"] = True

    # --------------------------------------------------------
    # reason
    # --------------------------------------------------------

    existing_reason = question.get(
        "reason"
    )

    if existing_reason is None:
        question["reason"] = reason

        return

    if isinstance(
        existing_reason,
        str,
    ):

        if not existing_reason.strip():
            question["reason"] = reason

        elif reason not in existing_reason:
            question["reason"] = (
                existing_reason.rstrip()
                + "\n"
                + reason
            )

        return

    # Unexpected existing type:
    # preserve the information by converting it into text
    # rather than silently destroying it.
    question["reason"] = (
        f"{existing_reason!r}\n{reason}"
    )


def _initialize_modification_fields(
    question: dict[str, Any],
) -> None:
    """
    Ensure every question has the modification fields.

    This does NOT mark a question modified.

    Missing fields become:

        modified: false
        reason: null

    Existing values are preserved exactly.
    """

    if "modified" not in question:
        question["modified"] = False

    if "reason" not in question:
        question["reason"] = None


# ============================================================
# OPTION MATCHING
# ============================================================

def _find_matching_original_option(
    validation_option: dict[str, Any],
    original_options: list[dict[str, Any]],
    used_original_indices: set[int],
) -> tuple[int | None, str | None, float]:
    """
    Match a validation option to an original option.

    Strategy:

    1. Exact option ID + sufficiently similar text.
    2. Otherwise find the best remaining option by text.
    3. Accept the text match only when similarity reaches
       OPTION_TEXT_SIMILARITY_THRESHOLD.

    Returns:

        (
            matched_original_index,
            "id" / "text" / None,
            similarity
        )
    """

    validation_option_object = validation_option.get(
        "option"
    )

    if not isinstance(
        validation_option_object,
        dict,
    ):
        return (
            None,
            None,
            0.0,
        )

    validation_id = validation_option_object.get(
        "id"
    )

    validation_text = validation_option_object.get(
        "text"
    )

    if not isinstance(
        validation_text,
        str,
    ):
        return (
            None,
            None,
            0.0,
        )

    # --------------------------------------------------------
    # 1. Exact ID
    # --------------------------------------------------------

    if isinstance(
        validation_id,
        str,
    ):

        for index, original_option in enumerate(
            original_options
        ):

            if index in used_original_indices:
                continue

            original_id = original_option.get(
                "id"
            )

            if original_id != validation_id:
                continue

            original_text = original_option.get(
                "text"
            )

            similarity = _option_text_similarity(
                validation_text,
                original_text,
            )

            if (
                similarity
                >= OPTION_TEXT_SIMILARITY_THRESHOLD
            ):
                return (
                    index,
                    "id",
                    similarity,
                )

            # Same ID but materially different text.
            # Do not trust the ID; continue with text matching.
            break

    # --------------------------------------------------------
    # 2. Text matching
    # --------------------------------------------------------

    best_index: int | None = None
    best_similarity = 0.0

    for index, original_option in enumerate(
        original_options
    ):

        if index in used_original_indices:
            continue

        original_text = original_option.get(
            "text"
        )

        if not isinstance(
            original_text,
            str,
        ):
            continue

        similarity = _option_text_similarity(
            validation_text,
            original_text,
        )

        if similarity > best_similarity:
            best_similarity = similarity
            best_index = index

    if (
        best_index is not None
        and best_similarity
        >= OPTION_TEXT_SIMILARITY_THRESHOLD
    ):

        return (
            best_index,
            "text",
            best_similarity,
        )

    return (
        None,
        None,
        best_similarity,
    )


# ============================================================
# MAIN FUNCTION
# ============================================================

def reconcile_option_consistency(
    node_id: str,
) -> dict[str, Any]:
    """
    Reconcile option consistency between:

        questions/valid/<node_id>.json

    and:

        validations/valid/<node_id>.json

    The validation result is treated as the authoritative
    source for the independently verified answer set.

    For each retained question:

        - option.correct values are synchronized with
          verified_correct_option_ids
        - correct_option_ids is synchronized
        - modified is persistently tracked
        - reason is persistently accumulated

    A question can become:

        modified: false -> true

    but never:

        true -> false

    Questions that cannot be safely reconciled are moved to:

        validations/invalid/<node_id>.json
        questions/orphan/<node_id>.json

    Existing archive files are append-only.
    """

    stem = _safe_node_id(
        node_id
    )

    # ========================================================
    # Locate files
    # ========================================================

    questions_path = _find_json_file(
        QUESTIONS_VALID_DIR,
        stem,
    )

    validation_path = _find_json_file(
        VALIDATIONS_VALID_DIR,
        stem,
    )

    metadata_path = (
        VALIDATIONS_METADATA_DIR
        / f"{stem}_metadata.json"
    )

    # ========================================================
    # Load files
    # ========================================================

    questions_data = _load_json_file(
        questions_path
    )

    validation_data = _load_json_file(
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
            f"'{questions_path}' must contain "
            f"a 'questions' list."
        )

    if not isinstance(
        validation_questions,
        list,
    ):
        raise ValueError(
            f"'{validation_path}' must contain "
            f"a 'questions' list."
        )

    # ========================================================
    # Initialize modification fields on ALL questions
    # ========================================================

    for question in questions:

        if isinstance(
            question,
            dict,
        ):
            _initialize_modification_fields(
                question
            )

    # ========================================================
    # Map original questions by ID
    # ========================================================

    questions_by_id: dict[
        str,
        tuple[int, dict[str, Any]],
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
                f"does not contain a valid ID."
            )

        if question_id in questions_by_id:
            raise ValueError(
                f"Duplicate original question ID: "
                f"{question_id}"
            )

        questions_by_id[
            question_id
        ] = (
            question_index,
            question,
        )

    # ========================================================
    # Statistics
    # ========================================================

    stats = {
        "questions_checked": 0,
        "questions_retained": 0,
        "questions_invalidated": 0,

        "options_checked": 0,

        "options_matched_by_id": 0,
        "options_matched_by_text": 0,

        "option_ids_repaired": 0,
        "option_texts_repaired": 0,
        "option_order_repairs": 0,

        "original_correct_repairs": 0,

        "question_correct_flags_repaired": 0,
        "question_correct_option_ids_repaired": 0,

        "missing_options": 0,
        "unmatched_options": 0,
        "ambiguous_options": 0,
    }

    # ========================================================
    # Output collections
    # ========================================================

    kept_validation_questions: list[
        dict[str, Any]
    ] = []

    invalid_original_questions: list[
        dict[str, Any]
    ] = []

    invalid_validation_questions: list[
        dict[str, Any]
    ] = []

    # ========================================================
    # Process every validation question
    # ========================================================

    for validation_question in validation_questions:

        stats[
            "questions_checked"
        ] += 1

        # ----------------------------------------------------
        # Validation question must be an object
        # ----------------------------------------------------

        if not isinstance(
            validation_question,
            dict,
        ):

            stats[
                "questions_invalidated"
            ] += 1

            invalid_validation_questions.append(
                validation_question
            )

            continue

        validation_question_id = validation_question.get(
            "id"
        )

        # ----------------------------------------------------
        # Corresponding original question
        # ----------------------------------------------------

        if (
            not isinstance(
                validation_question_id,
                str,
            )
            or validation_question_id
            not in questions_by_id
        ):

            stats[
                "questions_invalidated"
            ] += 1

            invalid_validation_questions.append(
                validation_question
            )

            continue

        _, original_question = (
            questions_by_id[
                validation_question_id
            ]
        )

        original_options = original_question.get(
            "options"
        )

        answer_correctness = validation_question.get(
            "answer_correctness"
        )

        if isinstance(
            answer_correctness,
            dict,
        ):
            validation_options = (
                answer_correctness.get(
                    "option_validations"
                )
            )

            verified_correct_option_ids = (
                answer_correctness.get(
                    "verified_correct_option_ids"
                )
            )

        else:
            validation_options = None
            verified_correct_option_ids = None

        # ----------------------------------------------------
        # Basic structure
        # ----------------------------------------------------

        if not isinstance(
            original_options,
            list,
        ):

            stats[
                "questions_invalidated"
            ] += 1

            invalid_original_questions.append(
                original_question
            )

            invalid_validation_questions.append(
                validation_question
            )

            continue

        if not isinstance(
            validation_options,
            list,
        ):

            stats[
                "questions_invalidated"
            ] += 1

            invalid_original_questions.append(
                original_question
            )

            invalid_validation_questions.append(
                validation_question
            )

            continue

        if not isinstance(
            verified_correct_option_ids,
            list,
        ):

            stats[
                "questions_invalidated"
            ] += 1

            invalid_original_questions.append(
                original_question
            )

            invalid_validation_questions.append(
                validation_question
            )

            continue

        # ----------------------------------------------------
        # Option count must match
        # ----------------------------------------------------

        if len(original_options) != len(
            validation_options
        ):

            stats[
                "missing_options"
            ] += abs(
                len(original_options)
                - len(validation_options)
            )

            stats[
                "questions_invalidated"
            ] += 1

            invalid_original_questions.append(
                original_question
            )

            invalid_validation_questions.append(
                validation_question
            )

            continue

        # ----------------------------------------------------
        # Match validation options to original options
        # ----------------------------------------------------

        used_original_indices: set[int] = set()

        repaired_options_by_original_index: dict[
            int,
            dict[str, Any],
        ] = {}

        question_is_valid = True
        saw_reordering = False

        for validation_option_index, validation_option in enumerate(
            validation_options
        ):

            stats[
                "options_checked"
            ] += 1

            if not isinstance(
                validation_option,
                dict,
            ):

                question_is_valid = False

                stats[
                    "unmatched_options"
                ] += 1

                break

            (
                matched_original_index,
                match_method,
                similarity,
            ) = _find_matching_original_option(
                validation_option=validation_option,
                original_options=original_options,
                used_original_indices=used_original_indices,
            )

            if matched_original_index is None:

                question_is_valid = False

                stats[
                    "unmatched_options"
                ] += 1

                break

            if matched_original_index in used_original_indices:

                question_is_valid = False

                stats[
                    "ambiguous_options"
                ] += 1

                break

            used_original_indices.add(
                matched_original_index
            )

            original_option = original_options[
                matched_original_index
            ]

            # ------------------------------------------------
            # Matching statistics
            # ------------------------------------------------

            if match_method == "id":

                stats[
                    "options_matched_by_id"
                ] += 1

            elif match_method == "text":

                stats[
                    "options_matched_by_text"
                ] += 1

            # ------------------------------------------------
            # Ordering
            # ------------------------------------------------

            if (
                matched_original_index
                != validation_option_index
            ):

                saw_reordering = True

            # ------------------------------------------------
            # Validation option reference
            # ------------------------------------------------

            validation_option_reference = (
                validation_option.get(
                    "option"
                )
            )

            if not isinstance(
                validation_option_reference,
                dict,
            ):

                question_is_valid = False

                stats[
                    "unmatched_options"
                ] += 1

                break

            repaired_validation_option = dict(
                validation_option
            )

            repaired_reference = dict(
                validation_option_reference
            )

            # =================================================
            # Authoritative option ID
            # =================================================

            old_id = repaired_reference.get(
                "id"
            )

            authoritative_id = original_option.get(
                "id"
            )

            if old_id != authoritative_id:

                stats[
                    "option_ids_repaired"
                ] += 1

            repaired_reference[
                "id"
            ] = authoritative_id

            # =================================================
            # Authoritative option text
            # =================================================

            old_text = repaired_reference.get(
                "text"
            )

            authoritative_text = original_option.get(
                "text"
            )

            if old_text != authoritative_text:

                stats[
                    "option_texts_repaired"
                ] += 1

            repaired_reference[
                "text"
            ] = authoritative_text

            repaired_validation_option[
                "option"
            ] = repaired_reference

            # =================================================
            # Authoritative original_correct
            # =================================================

            authoritative_original_correct = (
                original_option.get(
                    "correct"
                )
            )

            old_original_correct = (
                repaired_validation_option.get(
                    "original_correct"
                )
            )

            if (
                old_original_correct
                != authoritative_original_correct
            ):

                stats[
                    "original_correct_repairs"
                ] += 1

            repaired_validation_option[
                "original_correct"
            ] = authoritative_original_correct

            repaired_options_by_original_index[
                matched_original_index
            ] = repaired_validation_option

        # ----------------------------------------------------
        # Every original option must have been matched
        # ----------------------------------------------------

        if (
            question_is_valid
            and len(used_original_indices)
            != len(original_options)
        ):

            question_is_valid = False

            stats[
                "missing_options"
            ] += (
                len(original_options)
                - len(used_original_indices)
            )

        # ----------------------------------------------------
        # Invalid question
        # ----------------------------------------------------

        if not question_is_valid:

            stats[
                "questions_invalidated"
            ] += 1

            invalid_original_questions.append(
                original_question
            )

            invalid_validation_questions.append(
                validation_question
            )

            continue

        # ----------------------------------------------------
        # Option ordering repair
        # ----------------------------------------------------

        if saw_reordering:

            stats[
                "option_order_repairs"
            ] += 1

        # ====================================================
        # Rebuild validation options in authoritative order
        # ====================================================

        reordered_validation_options = [
            repaired_options_by_original_index[
                index
            ]
            for index in range(
                len(original_options)
            )
        ]

        answer_correctness[
            "option_validations"
        ] = reordered_validation_options

        # ====================================================
        # AUTHORITATIVE VERIFIED ANSWERS
        # ====================================================

        verified_correct_ids = [
            option_id
            for option_id in verified_correct_option_ids
            if isinstance(
                option_id,
                str,
            )
        ]

        verified_correct_id_set = set(
            verified_correct_ids
        )

        # ----------------------------------------------------
        # Validate that verified IDs actually correspond to
        # original options.
        # ----------------------------------------------------

        original_option_id_set = {
            option.get("id")
            for option in original_options
            if isinstance(
                option,
                dict,
            )
            and isinstance(
                option.get("id"),
                str,
            )
        }

        unknown_verified_ids = (
            verified_correct_id_set
            - original_option_id_set
        )

        if unknown_verified_ids:

            stats[
                "questions_invalidated"
            ] += 1

            invalid_original_questions.append(
                original_question
            )

            invalid_validation_questions.append(
                validation_question
            )

            continue

        # ====================================================
        # Synchronize the QUESTION itself
        # ====================================================

        question_was_modified = False
        modification_reasons: list[str] = []

        # ----------------------------------------------------
        # Correct flags
        # ----------------------------------------------------

        for option in original_options:

            option_id = option.get(
                "id"
            )

            if not isinstance(
                option_id,
                str,
            ):
                continue

            expected_correct = (
                option_id
                in verified_correct_id_set
            )

            current_correct = option.get(
                "correct"
            )

            if current_correct != expected_correct:

                option["correct"] = expected_correct

                question_was_modified = True

                stats[
                    "question_correct_flags_repaired"
                ] += 1

                modification_reasons.append(
                    f'Option "{option_id}" correct flag '
                    f'changed from {current_correct!r} '
                    f"to {expected_correct!r} according to "
                    f"the independently verified validation result."
                )

        # ----------------------------------------------------
        # correct_option_ids
        # ----------------------------------------------------

        current_correct_option_ids = (
            original_question.get(
                "correct_option_ids"
            )
        )

        if not isinstance(
            current_correct_option_ids,
            list,
        ):
            current_correct_option_ids = []

        # Preserve original option order.
        authoritative_correct_option_ids = [
            option.get("id")
            for option in original_options
            if (
                isinstance(
                    option,
                    dict,
                )
                and isinstance(
                    option.get("id"),
                    str,
                )
                and option.get("id")
                in verified_correct_id_set
            )
        ]

        if current_correct_option_ids != (
            authoritative_correct_option_ids
        ):

            original_question[
                "correct_option_ids"
            ] = authoritative_correct_option_ids

            question_was_modified = True

            stats[
                "question_correct_option_ids_repaired"
            ] += 1

            modification_reasons.append(
                "correct_option_ids synchronized with "
                "the independently verified correct option set: "
                f"{authoritative_correct_option_ids!r}."
            )

        # ====================================================
        # Persist modified / reason
        # ====================================================

        if question_was_modified:

            combined_reason = (
                "Option-answer consistency adjustment: "
                + " ".join(
                    modification_reasons
                )
            )

            _record_question_modification(
                original_question,
                combined_reason,
            )

        else:

            #
            # Do NOT alter an existing modified=True value.
            # Do NOT overwrite an existing reason.
            #
            # Only ensure missing fields exist.
            #
            _initialize_modification_fields(
                original_question
            )

        # ====================================================
        # Synchronize validation answer arrays
        # ====================================================

        original_correct_ids = (
            original_question.get(
                "correct_option_ids",
                [],
            )
        )

        answer_correctness[
            "provided_correct_option_ids"
        ] = list(
            original_correct_ids
        )

        answer_correctness[
            "verified_correct_option_ids"
        ] = authoritative_correct_option_ids

        answer_correctness[
            "valid"
        ] = (
            set(
                authoritative_correct_option_ids
            )
            == set(
                original_correct_ids
            )
        )

        kept_validation_questions.append(
            validation_question
        )

        stats[
            "questions_retained"
        ] += 1

    # ========================================================
    # SAVE VALID QUESTIONS
    # ========================================================

    _save_json_file(
        questions_path,
        {
            "questions": questions
        },
    )

    # ========================================================
    # SAVE VALID VALIDATIONS
    # ========================================================

    _save_json_file(
        validation_path,
        {
            "questions": kept_validation_questions
        },
    )

    # ========================================================
    # APPEND INVALID VALIDATIONS
    # ========================================================

    invalid_validation_path = (
        VALIDATIONS_INVALID_DIR
        / f"{stem}.json"
    )

    _append_questions_to_archive(
        invalid_validation_path,
        invalid_validation_questions,
    )

    # ========================================================
    # APPEND ORPHAN QUESTIONS
    # ========================================================

    orphan_questions_path = (
        QUESTIONS_ORPHAN_DIR
        / f"{stem}.json"
    )

    _append_questions_to_archive(
        orphan_questions_path,
        invalid_original_questions,
    )

    # ========================================================
    # METADATA
    # ========================================================

    if metadata_path.exists():

        metadata = _load_json_file(
            metadata_path
        )

    else:

        metadata = {
            "node_id": stem
        }

    metadata[
        "node_id"
    ] = stem

    metadata[
        "option_consistency"
    ] = {
        "questions_checked": stats[
            "questions_checked"
        ],
        "questions_retained": stats[
            "questions_retained"
        ],
        "questions_invalidated": stats[
            "questions_invalidated"
        ],
        "options_checked": stats[
            "options_checked"
        ],
        "options_matched_by_id": stats[
            "options_matched_by_id"
        ],
        "options_matched_by_text": stats[
            "options_matched_by_text"
        ],
        "option_text_similarity_threshold": (
            OPTION_TEXT_SIMILARITY_THRESHOLD
        ),
        "option_ids_repaired": stats[
            "option_ids_repaired"
        ],
        "option_texts_repaired": stats[
            "option_texts_repaired"
        ],
        "option_order_repairs": stats[
            "option_order_repairs"
        ],
        "original_correct_repairs": stats[
            "original_correct_repairs"
        ],
        "question_correct_flags_repaired": stats[
            "question_correct_flags_repaired"
        ],
        "question_correct_option_ids_repaired": stats[
            "question_correct_option_ids_repaired"
        ],
        "missing_options": stats[
            "missing_options"
        ],
        "unmatched_options": stats[
            "unmatched_options"
        ],
        "ambiguous_options": stats[
            "ambiguous_options"
        ],
    }

    metadata[
        "outputs"
    ] = {
        "valid_questions": str(
            questions_path
        ),
        "valid_validations": str(
            validation_path
        ),
        "invalid_validations": (
            str(invalid_validation_path)
            if invalid_validation_questions
            or invalid_validation_path.exists()
            else None
        ),
        "orphan_questions": (
            str(orphan_questions_path)
            if invalid_original_questions
            or orphan_questions_path.exists()
            else None
        ),
    }

    _save_json_file(
        metadata_path,
        metadata,
    )

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 72)
    print("OPTION CONSISTENCY RECONCILIATION COMPLETE")
    print("=" * 72)

    print(
        f"Node:                              {stem}"
    )

    print(
        f"Questions checked:                 "
        f"{stats['questions_checked']}"
    )

    print(
        f"Questions retained:                "
        f"{stats['questions_retained']}"
    )

    print(
        f"Questions invalidated:             "
        f"{stats['questions_invalidated']}"
    )

    print()

    print(
        f"Options checked:                   "
        f"{stats['options_checked']}"
    )

    print(
        f"Options matched by ID:             "
        f"{stats['options_matched_by_id']}"
    )

    print(
        f"Options matched by text:           "
        f"{stats['options_matched_by_text']}"
    )

    print(
        f"Option IDs repaired:               "
        f"{stats['option_ids_repaired']}"
    )

    print(
        f"Option texts repaired:             "
        f"{stats['option_texts_repaired']}"
    )

    print(
        f"Option order repairs:              "
        f"{stats['option_order_repairs']}"
    )

    print(
        f"Validation original_correct "
        f"repairs:                           "
        f"{stats['original_correct_repairs']}"
    )

    print()

    print(
        f"Question correct-flag repairs:     "
        f"{stats['question_correct_flags_repaired']}"
    )

    print(
        f"Question correct_option_ids "
        f"repairs:                           "
        f"{stats['question_correct_option_ids_repaired']}"
    )

    print()

    print(
        f"Missing options:                   "
        f"{stats['missing_options']}"
    )

    print(
        f"Unmatched options:                 "
        f"{stats['unmatched_options']}"
    )

    print(
        f"Ambiguous options:                 "
        f"{stats['ambiguous_options']}"
    )

    print()

    print(
        f"Questions file updated:             "
        f"{questions_path}"
    )

    print(
        f"Validation file updated:            "
        f"{validation_path}"
    )

    if invalid_validation_questions:

        print(
            f"Invalid validations appended to:   "
            f"{invalid_validation_path}"
        )

    if invalid_original_questions:

        print(
            f"Orphan questions appended to:      "
            f"{orphan_questions_path}"
        )

    print(
        f"Metadata:                           "
        f"{metadata_path}"
    )

    print("=" * 72)

    return metadata


# ============================================================
# EXECUTION
# ============================================================

if __name__ == "__main__":

    reconcile_option_consistency(
        node_id="isometries"
    )