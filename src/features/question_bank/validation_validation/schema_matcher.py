from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


# ============================================================
# INPUT DIRECTORIES
# ============================================================

QUESTIONS_INPUT_DIR = Path(
    r"F:\pythonProj\question_generator\llm_response_generations\jsons_with_ids"
)

VALIDATIONS_INPUT_DIR = Path(
    r"F:\pythonProj\question_generator\llm_validation\cleaned_json"
)


# ============================================================
# OUTPUT DIRECTORIES
# ============================================================

VALIDATIONS_OUTPUT_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\validations"
)

VALIDATIONS_VALID_DIR = (
    VALIDATIONS_OUTPUT_DIR / "valid"
)

VALIDATIONS_INVALID_DIR = (
    VALIDATIONS_OUTPUT_DIR / "invalid"
)

QUESTIONS_VALID_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\questions\valid"
)

QUESTIONS_ORPHAN_DIR = Path(
    r"F:\pythonProj\question_generator\final_schemas\questions\orphan"
)


# ============================================================
# CONFIGURATION
# ============================================================

# Minimum similarity accepted for fuzzy stem matching.
#
# 1.0 = identical after normalization
# 0.95 = extremely similar
# 0.90 = reasonably tolerant of small differences
#
# 0.92 is intentionally conservative.
STEM_SIMILARITY_THRESHOLD = 0.92


# ============================================================
# FILE DISCOVERY
# ============================================================

def _find_input_file(
    directory: Path,
    node_id: str,
) -> Path:
    """
    Find the input file corresponding to node_id.

    Supports:
        node_id = "isometries"
        node_id = "isometries.json"
        node_id = "isometries.txt"

    If no extension is supplied, .json is preferred over .txt.
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
    filename = Path(node_id).name

    suffix = Path(filename).suffix.lower()

    # Explicit extension.
    if suffix in {".json", ".txt"}:
        candidates = [
            filename
        ]

    # No extension.
    else:
        candidates = [
            f"{filename}.json",
            f"{filename}.txt",
        ]

    for candidate in candidates:

        path = directory / candidate

        if path.is_file():
            return path

    raise FileNotFoundError(
        f"Could not find input file for node_id='{node_id}'.\n"
        f"Directory: {directory}\n"
        f"Searched for: {', '.join(candidates)}"
    )


# ============================================================
# JSON LOADING
# ============================================================

def _load_json_file(
    path: Path,
) -> dict[str, Any]:
    """
    Load a JSON file containing an object at the root.
    """

    try:
        raw_text = path.read_text(
            encoding="utf-8"
        )
    except OSError as exc:
        raise OSError(
            f"Could not read '{path}': {exc}"
        ) from exc

    if not raw_text.strip():
        raise ValueError(
            f"File is empty: {path}"
        )

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in '{path}': {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Root JSON in '{path}' must be an object."
        )

    return data


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def _normalize_text(
    text: str,
) -> str:
    """
    Normalize question stems for tolerant comparison.

    The normalization intentionally ignores superficial differences
    such as:

        - leading/trailing whitespace
        - repeated whitespace
        - case differences
        - Unicode normalization
        - common punctuation differences

    It does NOT attempt semantic rewriting.
    """

    if not isinstance(text, str):
        return ""

    # Unicode normalization.
    text = unicodedata.normalize(
        "NFKC",
        text,
    )

    # Lowercase.
    text = text.casefold()

    # Normalize common Unicode punctuation variants.
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
        text = text.replace(old, new)

    # Collapse whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    # Remove spaces around punctuation.
    text = re.sub(
        r"\s*([,.;:!?()\[\]{}])\s*",
        r"\1",
        text,
    )

    return text.strip()


def _stem_similarity(
    stem_a: str,
    stem_b: str,
) -> float:
    """
    Calculate normalized fuzzy similarity between two stems.
    """

    normalized_a = _normalize_text(
        stem_a
    )

    normalized_b = _normalize_text(
        stem_b
    )

    if not normalized_a or not normalized_b:
        return 0.0

    if normalized_a == normalized_b:
        return 1.0

    return SequenceMatcher(
        None,
        normalized_a,
        normalized_b,
    ).ratio()


# ============================================================
# QUESTION STRUCTURE VALIDATION
# ============================================================

def _extract_questions(
    data: dict[str, Any],
    source_name: str,
) -> list[dict[str, Any]]:
    """
    Extract and validate the questions array from a JSON object.
    """

    questions = data.get(
        "questions"
    )

    if not isinstance(
        questions,
        list,
    ):
        raise ValueError(
            f"'{source_name}' must contain a "
            f"'questions' array."
        )

    result: list[dict[str, Any]] = []

    for index, question in enumerate(
        questions
    ):

        if not isinstance(
            question,
            dict,
        ):
            raise ValueError(
                f"{source_name}: question at index "
                f"{index} must be an object."
            )

        result.append(
            question
        )

    return result


# ============================================================
# STEM MATCHING
# ============================================================

def _find_stem_match(
    validation_question: dict[str, Any],
    questions: list[dict[str, Any]],
    used_question_indices: set[int],
) -> tuple[int | None, float]:
    """
    Search for the best unused question matching the validation
    question's stem.

    Returns:
        (matched_index, similarity)

    If no match reaches the configured threshold:
        (None, best_similarity)
    """

    validation_stem = validation_question.get(
        "stem"
    )

    if not isinstance(
        validation_stem,
        str,
    ):
        return None, 0.0

    best_index: int | None = None
    best_similarity = 0.0

    for question_index, question in enumerate(
        questions
    ):

        if question_index in used_question_indices:
            continue

        question_stem = question.get(
            "stem"
        )

        if not isinstance(
            question_stem,
            str,
        ):
            continue

        similarity = _stem_similarity(
            validation_stem,
            question_stem,
        )

        if similarity > best_similarity:
            best_similarity = similarity
            best_index = question_index

    if (
        best_index is not None
        and best_similarity >= STEM_SIMILARITY_THRESHOLD
    ):
        return (
            best_index,
            best_similarity,
        )

    return (
        None,
        best_similarity,
    )


# ============================================================
# MAIN RECONCILIATION FUNCTION
# ============================================================

def reconcile_question_validation(
    node_id: str,
) -> dict[str, Any]:
    """
    Reconcile generated questions-with-IDs against their LLM
    validation results.

    Algorithm:

    1. Load the questions JSON.
    2. Load the validation JSON.
    3. Process validation questions sequentially.
    4. Try to match by question ID.
    5. If the ID exists, verify the stems.
    6. If the ID match fails stem verification, search by stem.
    7. If stem matching succeeds, replace the validation ID
       with the authoritative question ID.
    8. If no stem match exists, move the validation question
       into validations/invalid.
    9. Save the resulting validation questions into
       validations/valid.
    10. Using the NEW valid validation file, determine which
        generated questions have corresponding validations.
    11. Save matched questions to questions/valid.
    12. Save unmatched questions to questions/orphan.
    13. Save reconciliation metadata.

    Returns:
        Metadata dictionary describing the reconciliation.
    """

    # ========================================================
    # Validate node_id
    # ========================================================

    if not isinstance(
        node_id,
        str,
    ):
        raise TypeError(
            "node_id must be a string."
        )

    node_id = node_id.strip()

    if not node_id:
        raise ValueError(
            "node_id cannot be empty."
        )

    # Use only the filename component.
    safe_node_id = Path(node_id).name

    # ========================================================
    # Locate inputs
    # ========================================================

    questions_path = _find_input_file(
        QUESTIONS_INPUT_DIR,
        safe_node_id,
    )

    validation_path = _find_input_file(
        VALIDATIONS_INPUT_DIR,
        safe_node_id,
    )

    # ========================================================
    # Load input JSON
    # ========================================================

    questions_data = _load_json_file(
        questions_path
    )

    validation_data = _load_json_file(
        validation_path
    )

    questions = _extract_questions(
        questions_data,
        str(questions_path),
    )

    validation_questions = _extract_questions(
        validation_data,
        str(validation_path),
    )

    # ========================================================
    # Validation of generated question IDs
    # ========================================================

    question_id_to_index: dict[str, int] = {}

    for index, question in enumerate(
        questions
    ):

        question_id = question.get(
            "id"
        )

        if not isinstance(
            question_id,
            str,
        ):
            raise ValueError(
                f"Question at index {index} in "
                f"'{questions_path}' has no valid string ID."
            )

        if question_id in question_id_to_index:
            raise ValueError(
                f"Duplicate question ID '{question_id}' "
                f"in '{questions_path}'."
            )

        question_id_to_index[
            question_id
        ] = index

    # ========================================================
    # Track matched generated questions
    # ========================================================

    used_question_indices: set[int] = set()

    # ========================================================
    # Output collections
    # ========================================================

    valid_validation_questions: list[
        dict[str, Any]
    ] = []

    invalid_validation_questions: list[
        dict[str, Any]
    ] = []

    # ========================================================
    # Metadata counters
    # ========================================================

    matched_by_id = 0
    matched_by_stem = 0
    invalid_validation_count = 0

    # Useful diagnostic information.
    id_match_stem_mismatch_count = 0
    stem_similarity_matches: list[float] = []

    # ========================================================
    # Process validation questions sequentially
    # ========================================================

    for validation_index, validation_question in enumerate(
        validation_questions
    ):

        validation_id = validation_question.get(
            "id"
        )

        validation_stem = validation_question.get(
            "stem"
        )

        matched_question_index: int | None = None

        # ----------------------------------------------------
        # First try exact ID matching
        # ----------------------------------------------------

        if isinstance(
            validation_id,
            str,
        ):

            question_index = question_id_to_index.get(
                validation_id
            )

            if (
                question_index is not None
                and question_index not in used_question_indices
            ):

                question = questions[
                    question_index
                ]

                question_stem = question.get(
                    "stem"
                )

                similarity = _stem_similarity(
                    validation_stem,
                    question_stem,
                )

                # --------------------------------------------
                # ID + sufficiently similar stem
                # --------------------------------------------

                if (
                    similarity
                    >= STEM_SIMILARITY_THRESHOLD
                ):

                    matched_question_index = (
                        question_index
                    )

                    matched_by_id += 1

                    stem_similarity_matches.append(
                        similarity
                    )

                # --------------------------------------------
                # ID exists but stems differ too much
                # --------------------------------------------

                else:

                    id_match_stem_mismatch_count += 1

        # ----------------------------------------------------
        # If ID matching failed, search by stem
        # ----------------------------------------------------

        if matched_question_index is None:

            (
                stem_match_index,
                stem_similarity,
            ) = _find_stem_match(
                validation_question=validation_question,
                questions=questions,
                used_question_indices=used_question_indices,
            )

            if stem_match_index is not None:

                matched_question_index = (
                    stem_match_index
                )

                matched_by_stem += 1

                stem_similarity_matches.append(
                    stem_similarity
                )

                # --------------------------------------------
                # Correct validation ID using authoritative
                # question ID.
                # --------------------------------------------

                authoritative_question = questions[
                    stem_match_index
                ]

                authoritative_id = authoritative_question.get(
                    "id"
                )

                if not isinstance(
                    authoritative_id,
                    str,
                ):
                    raise ValueError(
                        f"Matched question at index "
                        f"{stem_match_index} has invalid ID."
                    )

                validation_question[
                    "id"
                ] = authoritative_id

        # ----------------------------------------------------
        # No match found
        # ----------------------------------------------------

        if matched_question_index is None:

            invalid_validation_questions.append(
                validation_question
            )

            invalid_validation_count += 1

            continue

        # ----------------------------------------------------
        # Record generated question as used
        # ----------------------------------------------------

        used_question_indices.add(
            matched_question_index
        )

        # ----------------------------------------------------
        # Store valid validation question
        # ----------------------------------------------------

        valid_validation_questions.append(
            validation_question
        )

    # ========================================================
    # Construct NEW validation JSON
    # ========================================================

    valid_validation_data = {
        "questions": valid_validation_questions
    }

    invalid_validation_data = {
        "questions": invalid_validation_questions
    }

    # ========================================================
    # Prepare output directories
    # ========================================================

    VALIDATIONS_VALID_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    VALIDATIONS_INVALID_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    QUESTIONS_VALID_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    QUESTIONS_ORPHAN_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    VALIDATIONS_OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # Determine output filenames
    # ========================================================

    # Preserve .json if node_id has it.
    # Otherwise use .json as the final structured format.

    original_suffix = Path(
        safe_node_id
    ).suffix.lower()

    if original_suffix not in {
        ".json",
        ".txt",
    }:
        output_filename = (
            f"{safe_node_id}.json"
        )

    else:
        # Since these are final JSON schemas, force .json.
        output_filename = (
            f"{Path(safe_node_id).stem}.json"
        )

    # ========================================================
    # Save valid validation schema
    # ========================================================

    valid_validation_path = (
        VALIDATIONS_VALID_DIR
        / output_filename
    )

    valid_validation_path.write_text(
        json.dumps(
            valid_validation_data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # ========================================================
    # Save invalid validation schema
    # ========================================================

    invalid_validation_path: Path | None = None

    if invalid_validation_questions:

        invalid_filename = (
            f"{Path(safe_node_id).stem}_invalid.json"
        )

        invalid_validation_path = (
            VALIDATIONS_INVALID_DIR
            / invalid_filename
        )

        invalid_validation_path.write_text(
            json.dumps(
                invalid_validation_data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    # ========================================================
    # Build IDs from NEW valid validation schema
    # ========================================================

    valid_validation_ids: set[str] = set()

    for validation_question in (
        valid_validation_questions
    ):

        validation_id = validation_question.get(
            "id"
        )

        if isinstance(
            validation_id,
            str,
        ):
            valid_validation_ids.add(
                validation_id
            )

    # ========================================================
    # Split generated questions into:
    #
    #   questions/valid
    #   questions/orphan
    # ========================================================

    valid_questions: list[
        dict[str, Any]
    ] = []

    orphan_questions: list[
        dict[str, Any]
    ] = []

    for question in questions:

        question_id = question.get(
            "id"
        )

        if (
            isinstance(
                question_id,
                str,
            )
            and question_id in valid_validation_ids
        ):
            valid_questions.append(
                question
            )
        else:
            orphan_questions.append(
                question
            )

    # ========================================================
    # Save valid questions
    # ========================================================

    valid_questions_path = (
        QUESTIONS_VALID_DIR
        / output_filename
    )

    valid_questions_path.write_text(
        json.dumps(
            {
                "questions": valid_questions
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # ========================================================
    # Save orphan questions
    # ========================================================

    orphan_questions_path: Path | None = None

    if orphan_questions:

        orphan_filename = (
            f"{Path(safe_node_id).stem}.json"
        )

        orphan_questions_path = (
            QUESTIONS_ORPHAN_DIR
            / orphan_filename
        )

        orphan_questions_path.write_text(
            json.dumps(
                {
                    "questions": orphan_questions
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    # ========================================================
    # Metadata
    # ========================================================

    average_stem_similarity = (
        sum(stem_similarity_matches)
        / len(stem_similarity_matches)
        if stem_similarity_matches
        else None
    )

    metadata = {
        "node_id": Path(
            safe_node_id
        ).stem,
        "input_files": {
            "questions": str(
                questions_path
            ),
            "validation": str(
                validation_path
            )
        },
        "matching": {
            "stem_similarity_threshold": STEM_SIMILARITY_THRESHOLD,
            "matched_by_id": matched_by_id,
            "matched_by_stem": matched_by_stem,
            "invalid_validation_questions": invalid_validation_count,
            "id_matched_but_stem_mismatch": (
                id_match_stem_mismatch_count
            ),
            "average_stem_similarity": (
                average_stem_similarity
            )
        },
        "counts": {
            "input_questions": len(
                questions
            ),
            "input_validation_questions": len(
                validation_questions
            ),
            "valid_validation_questions": len(
                valid_validation_questions
            ),
            "valid_questions": len(
                valid_questions
            ),
            "orphan_questions": len(
                orphan_questions
            )
        },
        "outputs": {
            "valid_validation": str(
                valid_validation_path
            ),
            "invalid_validation": (
                str(invalid_validation_path)
                if invalid_validation_path
                else None
            ),
            "valid_questions": str(
                valid_questions_path
            ),
            "orphan_questions": (
                str(orphan_questions_path)
                if orphan_questions_path
                else None
            )
        }
    }

    metadata_path = (
        VALIDATIONS_OUTPUT_DIR
        / f"{Path(safe_node_id).stem}_metadata.json"
    )

    metadata_path.write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # ========================================================
    # Report
    # ========================================================

    print(
        "=" * 72
    )
    print(
        "QUESTION / VALIDATION RECONCILIATION COMPLETE"
    )
    print(
        "=" * 72
    )

    print(
        f"Node ID:                         "
        f"{Path(safe_node_id).stem}"
    )

    print(
        f"Input questions:                 "
        f"{len(questions)}"
    )

    print(
        f"Input validation questions:     "
        f"{len(validation_questions)}"
    )

    print(
        f"Matched by ID:                   "
        f"{matched_by_id}"
    )

    print(
        f"Matched by stem:                 "
        f"{matched_by_stem}"
    )

    print(
        f"Invalid validation questions:    "
        f"{invalid_validation_count}"
    )

    print(
        f"Valid questions:                 "
        f"{len(valid_questions)}"
    )

    print(
        f"Orphan questions:                "
        f"{len(orphan_questions)}"
    )

    print()

    print(
        f"Valid validation: {valid_validation_path}"
    )

    if invalid_validation_path:
        print(
            f"Invalid validation: {invalid_validation_path}"
        )

    print(
        f"Valid questions: {valid_questions_path}"
    )

    if orphan_questions_path:
        print(
            f"Orphan questions: {orphan_questions_path}"
        )

    print(
        f"Metadata: {metadata_path}"
    )

    print(
        "=" * 72
    )

    return metadata


# ============================================================
# EXAMPLE
# ============================================================

if __name__ == "__main__":

    metadata = reconcile_question_validation(
        node_id="isometries"
    )

    print(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        )
    )