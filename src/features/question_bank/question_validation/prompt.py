from ..question_attributes.question_difficulty import (
    BLOOM_FRAMEWORK_TEXT, PER_LEVEL_GENERAL_RULES, CognitiveComplexity, HardnessPerLevel
)
from ..question_attributes.question_type import QuestionType
# BASE_VALIDATION_PROMPT, MSQ_VALIDATION_PROMPT, MSQ_VALIDATION_SCHEMA

BASE_VALIDATION_PROMPT="""
VERY IMPORTANT TO REMEMBER AND NOTE: your JSON output should strictly follow the schema, no mistakes, and the values shoul strictly follow the explanations and rules stated here. 

What I specifically care about: **proof of answerability and a traceable proof of the answer**
- should be designed as an evidence/verification system
"""
f"""
---->>> Here are the difficulty rules that you need to understand to validate the difficulty of the given questions JSON:
{BLOOM_FRAMEWORK_TEXT}
{PER_LEVEL_GENERAL_RULES}
{CognitiveComplexity.REMEMBER.value[1]}
{HardnessPerLevel.REMEMBER_DIFFICULTY.value[1]}
{CognitiveComplexity.UNDERSTAND.value[1]}
{HardnessPerLevel.UNDERSTAND_DIFFICULTY.value[1]}
{CognitiveComplexity.APPLY.value[1]}
{HardnessPerLevel.APPLY_DIFFICULTY.value[1]}
{CognitiveComplexity.ANALYZE.value[1]}
{HardnessPerLevel.ANALYZE_DIFFICULTY.value[1]}
""" + """
---->>> These rules should apply to every question type
# 1. **10 validation step** that you should follow: 
## 1. Source/evidence validation 

the relevent JSON part where you put the results of this step:
"Source_validation" : {
"answerable": "bool",
"evidence": "string",
"confidence":"Number"
}
- where 'confidence' is how much certain you are about your conclusion/judgement, which is a number between [0,1]

First establish:

> **Does the provided question actually contain enough information to answer the question?**
### Check:
- Are all required facts present?
- Are required definitions present?
- Are required relationships present?
- Are required numerical values present?
- Are required prerequisites available?
- Is external knowledge necessary?
- Is the answer uniquely determined?

### Example

Document:

> A triangle has a base of 10 cm and a height of 6 cm. 

Question:

> What is the area of the triangle?

so, we need to know the base, height  of the triangle to calculate area: (Its area is calculated using (A=\frac12 bh).)
Answerability:
check if base =  present
check if height= present

Therefore:  
"Source_validation" : {
"answerable": true,
"evidence": " formula required to calculate triangle area is (A=\frac12 bh) where b=base, h=height values are provided as 10 cm, 6 cm respectively",
"confidence": 1
}

##### But:

> What is the perimeter of the triangle?

is **not answerable** because the side lengths aren't provided.
Therefore:  
"Source_validation" : {
"answerable": "False",
"evidence": "formula required to calculate perimeter area is (P=a+b+c) where sides values were not provided",
"confidence": 1
}

### Important caveat
Some questions won't provide values, and would provide general variables or ask about the formula without requiring solving.
If that's the intentions of the question, then it's answerable if just the equation/rule is the only thing required. 


### Evidence completeness

This is slightly different from answerability.

You want to identify **exactly which evidence supports each part of the solution**.

For example:
Question:
> A car travels 120 km in 2 hours. What is its average speed?


Evidence:
E1:
distance = 120 km
E2:
time = 2 hours
E3:
speed = distance / time

Then proof becomes:
Given E1,E2,E3. Answer = 60 km/h


Therefore:  
"Source_validation" : {
"answerable": "True",
"evidence": "E1: distance = 120 km, E2: time = 2 hours, E3:speed = distance / time. Given E1,E2,E3. Answer = 60 km/h",
"confidence":1
}




# 2. Evidence provenance
the relevent JSON part where you put the results of this step:
"provenance" : {
"info_available": "bool",
"relevent_chunks": [{"text":"string","id":"Number"}],
"summary_info":"string"
}

here, you provide the relevent chunks proving that the question is actually about the source document.
Using the `chunks`'s `text` from the input JSON that is provided to you as your source. The chunks' `text` needn't have EXACT information in literal word similalrity, but they have to provide the knowledge required.
### Example
Question:
> A car travels 120 km in 2 hours. What is its average speed?

You check the chunks in the JSON given to you and see if any of the chunks provide info that is required by the question.
If chunks are found, then your output JSON becomes: 
"provenance" : {
"info_available": true,
"relevent_chunks": [{"text":"chunk1 text","id":1},{"text":"chunk2 text","id":2},{"text":"chunk3 text","id":3},{"text":"chunk4 text","id":4}],
"summary_info":"from chunks of id=1 we get info about definition of speed. in id=2 the equation of average speed is provided. from id=3 more info were provided about speed. from id=4 examples were provided. the info provided are sufficient to understand how to solve this problem"
}

# 3. Answer derivation / proof
the relevent JSON part where you put the results of this step:
"answer_correctness" : {
"valid": "bool",
"proof":[{"step":"string","comments":"string","step_number":"Number"}],
}
You need to generate a **solution trace**.

For example:

### Question

> A car travels 120 km in 2 hours. What is its average speed?
> provided answer: 60 km/h

YOU MUST FOLLOW THIS EXACT FORMAT:
### Proof
Step 1
Known:
d = 120 km
t = 2 h
Evidence:
E1, E2

Step 2
Formula:
v = d/t
Evidence:
E3

Step 3
Substitution:
v = 120/2

Step 4
result:
v = 60

Conclusion:
v = 60 km/h is correct

see how the steps are done? you must follow that format of steps. 
"answer_correctness" : {
"valid": true,
"proof":[
{"step":"Known: d = 120 km, t = 2 h","comment":"provided in question, Evidence:E1, E2","step_number":1},
{"step":"Formula: v = d/t","comment":"provided in the chunks, chunk id:2. Evidence:E3","step_number":2},
{"step":"Substitution:v = 120/2","comment":"by substituting E1,E2 in E3","step_number":3},
{"step":"result:v = 60","comment":"it's same as the answer provided","step_number":4},
]
}
- "valid": true. because the conclusion found the answer given with the question is correct. 

# 4. Topic validation
the relevent JSON part where you put the results of this step:
{"topic_relevence":{
"relevent_to_topic": "Boolean",
"confidence_in_judgement": "Number",
"reason":"string"
}}

if the question requires undersranding of matrices, but the topic is about calculus, then {"relevent_to_topic" :false}
if the question requires undersranding of matrices, the topic is about linear algebra, then {"relevent_to_topic" :true} as matrices is a subset of linear algebra.
so, you should follow the subset & prerequisite JSON tree provided above to know the dependencies and whether the question is valid in that sense. 
- `confidence_in_judgement` is how much you're confident in your judgement. number must be \in [0,1]
- `reason` is where you justify that judgement (why it's relvent or not relevent and why you have given level of confidence)

# 5. Question Difficulty validation
the relevent JSON part where you put the results of this step:
{"confidence_difficulty_relevence" :"Object"}
- Object = any {} block that is equivelent to the difficulty types

You should also validate whether the generated question actually has the intended difficulty.
For example, if the Input JSON provided to you is like:
"bloom_level": "remember",
"task_difficulty": 1,
"msq_difficulty": 2

in your JSON response becomes:
{"confidence_difficulty_relevence" :{
{"bloom_level":"remember","current_bloom_level_confidence": 0.7,"previous_bloom_level_confidence": null},
{"task_difficulty":1,"current_task_difficulty_confidence": 0.8,"previous_task_difficulty_confidence": null},
{"msq_difficulty":1 ,"current_msq_difficulty_confidence": 0.7,"previous_msq_difficulty_confidence": 0.2},
}}
note how in your JSON response. how do you keep 'previous` variables such as `previous_bloom_level_confidence` to `null` if you didn't change value from previous answer.
(`"bloom_level":"remember"` AND `"task_difficulty":1` stays same in the JSON input to you, and you agree with it, so it becomes in your output as well.)
(`"msq_difficulty":1` is current estimation after validation which is different from the provided JSON to which was `"msq_difficulty": 2`. so, this becomes `"previous_msq_difficulty_confidence": 0.2`)
Note: confidence values should always be \in [0,1]
Note: both the current and previous confidence values can be low(i.e: current=0.4 & previous=0.2), but the current should be the higher value. 

according to the explained rules of each difficulty we did, you verify.
""".strip()


MSQ_VALIDATION_PROMPT="""
---->>> these are general rules:
""" +f"""
{BASE_VALIDATION_PROMPT}
and here are the rules about the MSQ question type:
---->>>>> now explanation about question type, the rules, format & structure to follow:
{QuestionType.MSQ.value[1]}
"""+"""
---->>>These rules are MSQ specific: 
You are an evidence-based validator for Multiple Select Questions (MSQs).

Your primary goal is:

**PROVE WHETHER THE QUESTION IS ANSWERABLE AND WHETHER EVERY ANSWER OPTION IS CORRECT OR INCORRECT, USING TRACEABLE SOURCE EVIDENCE.**

Treat the task as an evidence-verification system, not as a question-generation task.

The input contains generated MSQ questions, their options, their proposed correct answers, justifications, difficulty metadata, question IDs, and source-document chunks.

You must validate each question independently.

# GENERAL MSQ VALIDATION PRINCIPLES

An MSQ is fundamentally a set of independently evaluable claims.

For every question:

1. Determine whether the stem is answerable.
2. Determine whether sufficient source evidence exists.
3. Evaluate EVERY option independently.
4. Determine whether each option is CORRECT or INCORRECT.
5. Compare your independently verified option classifications against
   `correct_option_ids`.
6. Determine whether the provided answer set is correct.
7. Verify the provided justification for EVERY option.
8. Produce a traceable proof showing why each option is correct or incorrect.
9. Validate topic relevance.
10. Validate Bloom level, task difficulty, MSQ difficulty.

Do NOT assume that an option is correct merely because:
- it appears in `correct_option_ids`;
- its `correct` field is true;
- its justification says it is correct.

Likewise, do NOT assume that an option is incorrect merely because:
- its `correct` field is false;
- it is absent from `correct_option_ids`;
- its justification claims that it is incorrect.

Independently verify every option.

The source chunks supplied in the input are the primary evidence for provenance.
Do not fabricate source chunks.

General background knowledge may be used when necessary to reason about
the subject matter, but distinguish source-supported conclusions from
externally supplied knowledge. If the question cannot be reliably answered
from the provided source and answering requires unavailable information,
mark the question as not answerable.


# INPUT QUESTION STRUCTURE


Each input question has approximately this structure:""" + f"{QuestionType.MSQ.value[1]}" + """
The question may have any number of options >= 4.

The output MUST NOT reproduce the options, their justifications, or the
original answer metadata.

The output must contain only:
- the exact input question `id`
- the exact input question `stem`
- the validation results defined below.


# CRITICAL QUESTION IDENTITY RULE


For every output question:

- Copy `id` EXACTLY from the corresponding input question.
- Copy `stem` EXACTLY from the corresponding input question.
- Never regenerate an ID.
- Never alter an ID.
- Never associate an ID with another question.
- Never associate one question's stem with another question's ID.
- Never rephrase or change question's `stem` letters or words in any form.
- Preserve the exact one-to-one correspondence between input questions
  and output validation objects.


IMPORTANT: If there are N input questions, there must be exactly N output validations.

Process questions independently and preserve their identity.


# 1. SOURCE / ANSWERABILITY VALIDATION


Output field for each question:

"Source_validation": {
  "answerable": true,
  "evidence": "string",
  "confidence": 0.0
}

`confidence` must always be a number in [0,1].

First determine:

**Does the provided question contain enough information to determine
the correct answer set?**

For an MSQ, answerability means that it is possible to determine,
for EVERY option, whether the option is correct or incorrect.

Check:

- Are all required facts present?
- Are all required definitions present?
- Are required relationships present?
- Are required numerical values present?
- Are required formulas or rules present?
- Are required prerequisites available?
- Is external knowledge necessary?
- Can each option be independently classified?
- Is the complete correct-option set uniquely determined?
- Is the distinction between correct and incorrect options sufficiently clear?
- Does the source contain enough information to resolve potentially
  ambiguous options?

IMPORTANT:

An MSQ is NOT answerable merely because some options can be verified.

For example, suppose an MSQ has options A, B, C, D and:
- A can be proven correct,
- B can be proven correct,
- C can be proven incorrect,
- D cannot be determined.

Then the MSQ is NOT fully answerable because the complete answer set
cannot be established.

Answerability requires sufficient evidence to classify ALL options.

### Example

Source:

"A triangle has a base of 10 cm and height of 6 cm."

Question:

"Which of the following statements are correct?
A. The area is 30 cm².
B. The area is 60 cm².
C. The area formula is A = 1/2 bh.
D. The perimeter is 30 cm."

If the source provides enough information to establish A, B and C but does
not provide the side lengths required to determine D, the question is NOT
fully answerable.

The issue is not merely whether the question has useful information.
The issue is whether the COMPLETE correct-option set can be established.

General conceptual MSQ

Some MSQs do not require numerical values.

For example:

"Which of the following are properties of isometries?"

If the source provides the definition and relevant properties of isometries,
the question may be fully answerable without numerical data.

# 2. EVIDENCE COMPLETENESS

Evidence completeness is distinct from answerability.

You must identify the evidence required to establish the truth value
of EACH OPTION.

For an MSQ, evidence must allow you to establish:

A = correct or incorrect
B = correct or incorrect
C = correct or incorrect
...

Do not provide evidence only for the options marked correct.

Incorrect options also require justification/evidence explaining why
they are incorrect.

For example:

Option A:
Evidence E1 says speed = distance / time.

Option B:
Evidence E2 gives the required numerical value.

Option C:
Evidence E3 states a condition that contradicts the option.

The proof must be able to trace every classification to evidence.

# 3. EVIDENCE PROVENANCE


Output field:

"provenance": {
  "info_available": true,
  "relevent_chunks": [
    {
      "text": "string",
      "id": 1
    }
  ],
  "summary_info": "string"
}

Use the `text` and `id` values from the source chunks supplied in the
input JSON.

Do not invent chunks!

A relevant chunk does not have to use the exact wording of the question.
It must contain knowledge that supports the reasoning required to validate
the question.

For an MSQ, include all source chunks materially used to determine
the truth value of ANY option.

If different options require different evidence, include all relevant
chunks.

If no source chunk provides the necessary information:

"info_available": false

and explain why in `summary_info`.


# 4. MSQ ANSWER CORRECTNESS / OPTION-BY-OPTION PROOF
Output field for EACH option: (each MSQ answer option will have this block)
"answer_correctness": {
  "option":{"id":"string","text":"string"},
  "original_correct":true
  "valid": true,
  "proof": [
    {
      "step": "string",
      "comments": "string",
      "step_number": 1
    }
  ]
}

This section is the core of the validation.

For an MSQ, `valid` means:

**The provided answer set is exactly correct.**

MANDATORY OPTION-BY-OPTION VALIDATION


You MUST evaluate EVERY option separately.

For each option:

1. Identify the option by its option ID.
2. State whether it is independently judged CORRECT or INCORRECT.
3. Explain why.
4. Cite the relevant source evidence/chunk IDs where applicable.
where chunk IDs are from the provenance you created for this specific question:
```
"provenance": {
  "info_available": true,
  "relevent_chunks": [
    {
      "text": "string",
      "id": 1
    }
  ],
  "summary_info": "string"
}
```

5. Compare the independently determined truth value with the
   input option's `correct` field(from the input JSON provided to you).
6. If the supplied `justification` is wrong or incomplete, identify that.


### Example
Question:
> A car travels 120 km in 2 hours. What is its average speed?
A) v = 60 km/h
B) ...
C) ...
D) ... 

Example proof: (this proof is done for each option)

see how structured the proof is? you must keep it as structured. 
Step 1:
### Proof
Step 1
Known:
d = 120 km
t = 2 h
Evidence:
E1, E2

Step 2
Formula:
v = d/t
Evidence:
E3

Step 3
Substitution:
v = 120/2

Step 4
result:
v = 60

Conclusion:
v = 60 km/h is correct

"answer_correctness" : {
"option":{"id":"A","text":"60 km/h"},
"original_correct":true
"valid": true,
"proof":[
{"step":"Known: d = 120 km, t = 2 h","comment":"provided in question, Evidence:E1, E2","step_number":1},
{"step":"Formula: v = d/t","comment":"provided in the chunks, chunk id:2. Evidence:E3","step_number":2},
{"step":"Substitution:v = 120/2","comment":"by substituting E1,E2 in E3","step_number":3},
{"step":"result:v = 60","comment":"it's same as the answer provided","step_number":4},
]
}
- `"original_correct":true` maps directly from the `correct` field from the JSON schema provided to you with the given option. 
- "valid": true. because the conclusion found the answer given with the question(`correct` from the JSON schema provided to you = `"original_correct":true`) to be correct. 



# 6. TOPIC VALIDATION
relevent JSON field Output:
{"topic_relevence":{
"relevent_to_topic": true,
"confidence_in_judgement": 0.0,
"reason":"string"
}}

Determine whether the question is relevant to the supplied topic.

Use the supplied subset/prerequisite JSON tree.

The answer MUST require understanding of the provied topic. But if it requires ALSO unerstanding of other topics that are pre-requisites or subsets, then it's fine. 
##### it's a problem ONLY when either
1) the answer requires ONLY pre-requisites or subsets of the topic but doesn't not require  understanding of the topic itself.
2) 
Example:

Topic = Linear Algebra

Question requires understanding matrices.

Matrices are a subset of Linear Algebra.

Therefore:

{"topic_relevence":{
"relevent_to_topic": true,
"confidence_in_judgement": 0.7,
"reason":"Topic = Linear Algebra. Question requires understanding matrices. Matrices are a subset of Linear Algebra. confience=0.7 because matrices is not everything in linear algebra"
}}

Example:

Topic = Calculus

Question requires understanding matrix transformation.

If the supplied JSON graph shows eigenvalues as a concept of Linear Algebra
rather than Calculus and there is no valid prerequisite/subset path making
it part of the topic scope:

{"topic_relevence":{
"relevent_to_topic": False,
"confidence_in_judgement": 0.9,
"reason":"Topic = Calculus. matrix transformation does not belong as subset or pre-requisite of Calculus. confidence=0.9 because the graph shows no connection between calculus and matrix transformation"
}}

Do not determine topic relevance solely from keyword overlap.


# 8. QUESTION DIFFICULTY VALIDATION


Output:

"confidence_difficulty_relevence": {
  "bloom_level": {
    "current": "remember",
    "current_confidence": 0.8,
    "previous_confidence": null
  },
  "task_difficulty": {
    "current": 2,
    "current_confidence": 0.9,
    "previous_confidence": null
  },
  "msq_difficulty": {
    "current": 2,
    "current_confidence": 0.85,
    "previous_confidence": null
  }
}


##### CONFIDENCE RULE

If you agrees with the original value:

Keep the original value as `current`.

Set `previous_confidence` to null.

Example:

Input:
"bloom_level": "remember"

You agree:
remember

Output:

"current": "remember",
"current_confidence": 0.9,
"previous_confidence": null

If the you decide to change the value:

`current` = new validated value

`current_confidence` = confidence in the new value

`previous_confidence` = confidence in the ORIGINAL supplied value

Example:

Input:
"msq_difficulty": 2

and your conclusion:
3

Output:

"current": 3,
"current_confidence": 0.85,
"previous_confidence": 0.55

The current confidence should be > previous confidence.

However, both may be low.

Example:

current = 0.4
previous = 0.2

is valid.

All confidence values must be in [0,1].

# THE MOST IMPROTANT TO FOLLOW: (CRITICAL & CRUCIAL)
### 1) following a prove like structure where you state the information in the step like:

Evidence:
E1:
distance = 120 km
E2:
time = 2 hours
E3:
speed = distance / time

Then proof becomes:
Given E1,E2,E3. Answer = 60 km/h


Therefore:  
"Source_validation" : {
"answerable": "True",
"evidence": "E1: distance = 120 km, E2: time = 2 hours, E3:speed = distance / time. Given E1,E2,E3. Answer = 60 km/h",
"confidence":1
}

### 2) Structuring in a verifiable steps like:
YOU MUST FOLLOW THIS EXACT FORMAT:
### Proof
Step 1
Known:
d = 120 km
t = 2 h
Evidence:
E1, E2

Step 2
Formula:
v = d/t
Evidence:
E3

Step 3
Substitution:
v = 120/2

Step 4
result:
v = 60

Conclusion:
v = 60 km/h is correct

see how the steps are done? you must follow that format of steps. 
"answer_correctness" : {
"valid": true,
"proof":[
{"step":"Known: d = 120 km, t = 2 h","comment":"provided in question, Evidence:E1, E2","step_number":1},
{"step":"Formula: v = d/t","comment":"provided in the chunks, chunk id:2. Evidence:E3","step_number":2},
{"step":"Substitution:v = 120/2","comment":"by substituting E1,E2 in E3","step_number":3},
{"step":"result:v = 60","comment":"it's same as the answer provided","step_number":4},
]
}
""".strip()


MSQ_VALIDATION_SCHEMA="""
These are MERELY examples of the schema structure you should follow as your output. you don't copy paste the values. You follow the instructions above, and generate JSON output for the JSON of questions provided to you above.  And you return JSON that verifies ALL the questions provided in the questions schema. ALL OF THEM!
```JSON
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MSQ Validation Response",
  "description": "Evidence-based validation results for Multiple Select Questions (MSQs). Each output object preserves only the exact question ID and exact question stem from the input, together with source validation, provenance, option-by-option answer validation, topic relevance, and difficulty validation.",
  "type": "object",
  "properties": {
    "questions": {
      "type": "array",
      "description": "Validation result for every input MSQ. The number, order, IDs, and stems must correspond exactly to the input questions.",
      "minItems": 1,
      "items": {
        "$ref": "#/definitions/question_validation"
      }
    }
  },
  "required": [
    "questions"
  ],
  "additionalProperties": false,

  "definitions": {

    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Confidence in the corresponding validation judgment. Must be between 0 and 1 inclusive."
    },

    "question_validation": {
      "type": "object",
      "description": "Complete validation result for one input MSQ.",
      "properties": {

        "id": {
          "type": "string",
          "description": "The exact question ID copied from the corresponding input question. It must not be regenerated, modified, or associated with another question."
        },

        "stem": {
          "type": "string",
          "description": "The exact question stem copied from the corresponding input question. It must not be rephrased, summarized, corrected, or associated with another question."
        },

        "Source_validation": {
          "$ref": "#/definitions/source_validation"
        },

        "provenance": {
          "$ref": "#/definitions/provenance"
        },

        "answer_correctness": {
          "$ref": "#/definitions/answer_correctness"
        },

        "topic_relevence": {
          "$ref": "#/definitions/topic_relevence"
        },

        "confidence_difficulty_relevence": {
          "$ref": "#/definitions/difficulty_validation"
        }
      },

      "required": [
        "id",
        "stem",
        "Source_validation",
        "provenance",
        "answer_correctness",
        "topic_relevence",
        "confidence_difficulty_relevence"
      ],

      "additionalProperties": false
    },

    "source_validation": {
      "type": "object",
      "description": "Determines whether the complete MSQ is answerable: sufficient information must exist to independently classify every option as correct or incorrect and uniquely determine the complete correct-option set.",
      "properties": {

        "answerable": {
          "type": "boolean",
          "description": "True only when sufficient information exists to determine the truth value of every option and therefore uniquely determine the complete correct-option set."
        },

        "evidence": {
          "type": "string",
          "description": "Explicit evidence-based explanation showing which facts, definitions, relationships, formulas, values, prerequisites, or other information establish answerability or explain why the question is not fully answerable."
        },

        "confidence": {
          "$ref": "#/definitions/confidence"
        }
      },

      "required": [
        "answerable",
        "evidence",
        "confidence"
      ],

      "additionalProperties": false
    },

    "provenance": {
      "type": "object",
      "description": "Source-document evidence used to establish the claims required to validate the MSQ and its individual options.",
      "properties": {

        "info_available": {
          "type": "boolean",
          "description": "Whether relevant information was found in the supplied source chunks."
        },

        "relevent_chunks": {
          "type": "array",
          "description": "The source chunks materially used for validating the question or its options. Their text and IDs must come from the supplied input and must not be fabricated.",
          "items": {
            "$ref": "#/definitions/relevant_chunk"
          }
        },

        "summary_info": {
          "type": "string",
          "description": "Explanation of what the selected source chunks establish and how they support the validation."
        }
      },

      "required": [
        "info_available",
        "relevent_chunks",
        "summary_info"
      ],

      "additionalProperties": false
    },

    "relevant_chunk": {
      "type": "object",
      "description": "A source chunk used as evidence for the validation.",
      "properties": {

        "text": {
          "type": "string",
          "description": "The exact text of the relevant source chunk from the input."
        },

        "id": {
          "type": "integer",
          "description": "The source chunk ID exactly as provided in the input."
        }
      },

      "required": [
        "text",
        "id"
      ],

      "additionalProperties": false
    },

    "answer_correctness": {
      "type": "object",
      "description": "MSQ answer validation. The top-level valid field evaluates the complete provided answer set. Each option is independently validated in option_validations.",
      "properties": {

        "valid": {
          "type": "boolean",
          "description": "True only when the complete set of independently verified correct options exactly matches the provided correct_option_ids set."
        },

        "verified_correct_option_ids": {
          "type": "array",
          "description": "Option IDs independently determined to be correct after evidence-based validation.",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },

        "provided_correct_option_ids": {
          "type": "array",
          "description": "The exact correct_option_ids supplied in the input question, copied without modification.",
          "items": {
            "type": "string"
          },
          "uniqueItems": true
        },

        "option_validations": {
          "type": "array",
          "description": "Independent validation of every answer option. There must be exactly one object for every input option, in the same order as the input options.",
          "minItems": 1,
          "items": {
            "$ref": "#/definitions/option_validation"
          }
        }
      },

      "required": [
        "valid",
        "verified_correct_option_ids",
        "provided_correct_option_ids",
        "option_validations"
      ],

      "additionalProperties": false
    },

    "option_validation": {
      "type": "object",
      "description": "Independent evidence-based validation of a single MSQ option.",
      "properties": {

        "option": {
          "$ref": "#/definitions/option_reference"
        },

        "original_correct": {
          "type": "boolean",
          "description": "The exact correct value copied from this option's input JSON. This must not be inferred or changed."
        },

        "valid": {
          "type": "boolean",
          "description": "Whether the independently determined truth value of this option agrees with its original correct field. True means the original correct/incorrect classification for this option is supported; false means it is not."
        },

        "independently_verified_correct": {
          "type": "boolean",
          "description": "The validator's independent determination of whether this option is actually correct."
        },

        "justification_correct": {
          "type": "boolean",
          "description": "Whether the justification supplied with the option is factually correct, relevant, and sufficient to support the option's claimed correct/incorrect status."
        },

        "proof": {
          "type": "array",
          "description": "Traceable proof establishing why this option is independently judged correct or incorrect.",
          "minItems": 1,
          "items": {
            "$ref": "#/definitions/proof_step"
          }
        }
      },

      "required": [
        "option",
        "original_correct",
        "valid",
        "independently_verified_correct",
        "justification_correct",
        "proof"
      ],

      "additionalProperties": false
    },

    "option_reference": {
      "type": "object",
      "description": "Exact identification of the option being validated.",
      "properties": {

        "id": {
          "type": "string",
          "description": "The exact option ID from the input, such as A, B, C, etc."
        },

        "text": {
          "type": "string",
          "description": "The exact option text copied from the input. It must not be rewritten or summarized."
        }
      },

      "required": [
        "id",
        "text"
      ],

      "additionalProperties": false
    },

    "proof_step": {
      "type": "object",
      "description": "One ordered step in the evidence-based proof.",
      "properties": {

        "step": {
          "type": "string",
          "description": "The reasoning, calculation, inference, classification, or conclusion performed in this step."
        },

        "comments": {
          "type": "string",
          "description": "Explanation of why the step is valid. Where applicable, identify the relevant source chunk IDs and distinguish supplied information from derived reasoning."
        },

        "step_number": {
          "type": "integer",
          "minimum": 1,
          "description": "Sequential number of the proof step."
        }
      },

      "required": [
        "step",
        "comments",
        "step_number"
      ],

      "additionalProperties": false
    },

    "topic_relevence": {
      "type": "object",
      "description": "Validation of whether the question actually requires understanding of the supplied topic, using the provided subset/prerequisite knowledge graph.",
      "properties": {

        "relevent_to_topic": {
          "type": "boolean",
          "description": "True when answering the question requires understanding of the supplied topic itself, possibly together with concepts that are valid prerequisites or subsets of that topic."
        },

        "confidence_in_judgement": {
          "$ref": "#/definitions/confidence"
        },

        "reason": {
          "type": "string",
          "description": "Evidence-based explanation of why the question is or is not relevant to the topic, including relevant subset/prerequisite relationships when applicable."
        }
      },

      "required": [
        "relevent_to_topic",
        "confidence_in_judgement",
        "reason"
      ],

      "additionalProperties": false
    },

    "difficulty_validation": {
      "type": "object",
      "description": "Validation of Bloom level, task difficulty, and MSQ-specific difficulty. When the validator agrees with the original value, previous_confidence must be null. When the validator changes the value, previous_confidence must contain confidence in the original value.",
      "properties": {

        "bloom_level": {
          "$ref": "#/definitions/bloom_validation"
        },

        "task_difficulty": {
          "$ref": "#/definitions/task_difficulty_validation"
        },

        "msq_difficulty": {
          "$ref": "#/definitions/msq_difficulty_validation"
        }
      },

      "required": [
        "bloom_level",
        "task_difficulty",
        "msq_difficulty"
      ],

      "additionalProperties": false
    },

    "bloom_validation": {
      "type": "object",
      "description": "Validation of the question's Bloom cognitive level.",
      "properties": {

        "current": {
          "type": "string",
          "enum": [
            "remember",
            "understand",
            "apply",
            "analyze",
            "evaluate",
            "create"
          ],
          "description": "The Bloom level independently determined by the validator."
        },

        "current_confidence": {
          "$ref": "#/definitions/confidence"
        },

        "previous_confidence": {
          "type": [
            "number",
            "null"
          ],
          "minimum": 0,
          "maximum": 1,
          "description": "Confidence in the original Bloom level supplied in the input. Must be null when the validator agrees with the original level."
        }
      },

      "required": [
        "current",
        "current_confidence",
        "previous_confidence"
      ],

      "additionalProperties": false
    },

    "task_difficulty_validation": {
      "type": "object",
      "description": "Validation of task difficulty on the 1-5 scale.",
      "properties": {

        "current": {
          "type": "integer",
          "minimum": 1,
          "maximum": 5,
          "description": "Task difficulty independently determined by the validator."
        },

        "current_confidence": {
          "$ref": "#/definitions/confidence"
        },

        "previous_confidence": {
          "type": [
            "number",
            "null"
          ],
          "minimum": 0,
          "maximum": 1,
          "description": "Confidence in the original task difficulty supplied in the input. Must be null when the validator agrees with the original difficulty."
        }
      },

      "required": [
        "current",
        "current_confidence",
        "previous_confidence"
      ],

      "additionalProperties": false
    },

    "msq_difficulty_validation": {
      "type": "object",
      "description": "Validation of MSQ-specific difficulty on the 1-3 scale.",
      "properties": {

        "current": {
          "type": "integer",
          "minimum": 1,
          "maximum": 3,
          "description": "MSQ difficulty independently determined by the validator."
        },

        "current_confidence": {
          "$ref": "#/definitions/confidence"
        },

        "previous_confidence": {
          "type": [
            "number",
            "null"
          ],
          "minimum": 0,
          "maximum": 1,
          "description": "Confidence in the original MSQ difficulty supplied in the input. Must be null when the validator agrees with the original difficulty."
        }
      },

      "required": [
        "current",
        "current_confidence",
        "previous_confidence"
      ],

      "additionalProperties": false
    }
  }
}
```
# JSON examples
### Mathematics:
```JSON
{
  "questions": [
    {
      "id": "q_math_001",
      "stem": "Which of the following transformations preserve distances in the plane? Select all that apply.",
      "Source_validation": {
        "answerable": true,
        "evidence": "E1: A reflection through a line preserves the distance between any two points. E2: A translation preserves the distance between any two points. E3: A rotation preserves the distance between any two points. E4: A dilation by a factor of 2 multiplies every distance by 2. Given E1, E2, E3, and E4, every option can be independently classified and the complete correct-option set is uniquely determined as A, B, and C.",
        "confidence": 0.99
      },
      "provenance": {
        "info_available": true,
        "relevent_chunks": [
          {
            "text": "A reflection through a line is an isometry and preserves the distance between every pair of points.",
            "id": 101
          },
          {
            "text": "A translation is an isometry and preserves the distance between every pair of points.",
            "id": 102
          },
          {
            "text": "A rotation is an isometry and preserves the distance between every pair of points.",
            "id": 103
          },
          {
            "text": "A dilation by a factor of 2 changes every distance by a factor of 2 and therefore does not preserve distances.",
            "id": 104
          }
        ],
        "summary_info": "E1-E4 provide the required definitions and properties for independently determining the truth value of every option."
      },
      "answer_correctness": {
        "valid": true,
        "verified_correct_option_ids": [
          "A",
          "B",
          "C"
        ],
        "provided_correct_option_ids": [
          "A",
          "B",
          "C"
        ],
        "option_validations": [
          {
            "option": {
              "id": "A",
              "text": "Reflection through a line."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Reflection through a line is an isometry.",
                "comments": "Evidence: E1, source chunk 101.",
                "step_number": 1
              },
              {
                "step": "Definition: An isometry preserves the distance between every pair of points.",
                "comments": "Evidence: E1, source chunk 101.",
                "step_number": 2
              },
              {
                "step": "Conclusion: Reflection through a line preserves distances and is therefore a correct option.",
                "comments": "The independent conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "B",
              "text": "Translation."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: A translation is an isometry.",
                "comments": "Evidence: E2, source chunk 102.",
                "step_number": 1
              },
              {
                "step": "Property: An isometry preserves distances between every pair of points.",
                "comments": "Evidence: E2, source chunk 102.",
                "step_number": 2
              },
              {
                "step": "Conclusion: A translation preserves distances and is therefore a correct option.",
                "comments": "The independent conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "C",
              "text": "Rotation."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: A rotation is an isometry.",
                "comments": "Evidence: E3, source chunk 103.",
                "step_number": 1
              },
              {
                "step": "Property: An isometry preserves distances.",
                "comments": "Evidence: E3, source chunk 103.",
                "step_number": 2
              },
              {
                "step": "Conclusion: A rotation preserves distances and is therefore a correct option.",
                "comments": "The independent conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "D",
              "text": "Dilation by a factor of 2."
            },
            "original_correct": false,
            "valid": true,
            "independently_verified_correct": false,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: A dilation by a factor of 2 multiplies every distance by 2.",
                "comments": "Evidence: E4, source chunk 104.",
                "step_number": 1
              },
              {
                "step": "Comparison: A distance-preserving transformation must leave every distance unchanged.",
                "comments": "Evidence: E1, E2, and E3 establish the distance-preserving criterion for isometries.",
                "step_number": 2
              },
              {
                "step": "Conclusion: A dilation by 2 does not preserve distances and is therefore incorrect.",
                "comments": "The independent conclusion agrees with original_correct = false.",
                "step_number": 3
              }
            ]
          }
        ]
      },
      "topic_relevence": {
        "relevent_to_topic": true,
        "confidence_in_judgement": 0.99,
        "reason": "The question directly requires understanding of isometries and distance-preserving transformations, which is the supplied geometry topic itself."
      },
      "confidence_difficulty_relevence": {
        "bloom_level": {
          "current": "remember",
          "current_confidence": 0.98,
          "previous_confidence": null
        },
        "task_difficulty": {
          "current": 1,
          "current_confidence": 0.99,
          "previous_confidence": null
        },
        "msq_difficulty": {
          "current": 2,
          "current_confidence": 0.97,
          "previous_confidence": null
        }
      }
    },
    {
      "id": "q_math_002",
      "stem": "If f(x) = 3x + 2, which of the following statements are correct? Select all that apply.",
      "Source_validation": {
        "answerable": true,
        "evidence": "E1: f(x) = 3x + 2. E2: f(0) = 3(0) + 2 = 2. E3: f(1) = 3(1) + 2 = 5. E4: f(2) = 3(2) + 2 = 8. E5: In f(x) = mx + b, the coefficient m is the slope, so the slope is 3. Given E1-E5, every option can be independently evaluated.",
        "confidence": 1.0
      },
      "provenance": {
        "info_available": true,
        "relevent_chunks": [
          {
            "text": "The function is defined as f(x) = 3x + 2.",
            "id": 201
          },
          {
            "text": "In slope-intercept form f(x) = mx + b, m represents the slope.",
            "id": 202
          }
        ],
        "summary_info": "The function rule in chunk 201 permits direct evaluation of the proposed values, while chunk 202 supplies the interpretation of the slope."
      },
      "answer_correctness": {
        "valid": true,
        "verified_correct_option_ids": [
          "A",
          "B",
          "D"
        ],
        "provided_correct_option_ids": [
          "A",
          "B",
          "D"
        ],
        "option_validations": [
          {
            "option": {
              "id": "A",
              "text": "f(0) = 2."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: f(x) = 3x + 2.",
                "comments": "Evidence: E1, source chunk 201.",
                "step_number": 1
              },
              {
                "step": "Substitution: f(0) = 3(0) + 2.",
                "comments": "The input value x = 0 is substituted into E1.",
                "step_number": 2
              },
              {
                "step": "Result: f(0) = 2.",
                "comments": "3(0) + 2 = 2.",
                "step_number": 3
              },
              {
                "step": "Conclusion: Option A is correct.",
                "comments": "The result agrees with original_correct = true.",
                "step_number": 4
              }
            ]
          },
          {
            "option": {
              "id": "B",
              "text": "f(1) = 5."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: f(x) = 3x + 2.",
                "comments": "Evidence: E1, source chunk 201.",
                "step_number": 1
              },
              {
                "step": "Substitution: f(1) = 3(1) + 2.",
                "comments": "The input value x = 1 is substituted into E1.",
                "step_number": 2
              },
              {
                "step": "Result: f(1) = 5.",
                "comments": "3(1) + 2 = 5.",
                "step_number": 3
              },
              {
                "step": "Conclusion: Option B is correct.",
                "comments": "The result agrees with original_correct = true.",
                "step_number": 4
              }
            ]
          },
          {
            "option": {
              "id": "C",
              "text": "f(2) = 7."
            },
            "original_correct": false,
            "valid": true,
            "independently_verified_correct": false,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: f(x) = 3x + 2.",
                "comments": "Evidence: E1, source chunk 201.",
                "step_number": 1
              },
              {
                "step": "Substitution: f(2) = 3(2) + 2.",
                "comments": "The input value x = 2 is substituted into E1.",
                "step_number": 2
              },
              {
                "step": "Result: f(2) = 8.",
                "comments": "3(2) + 2 = 8, not 7.",
                "step_number": 3
              },
              {
                "step": "Conclusion: Option C is incorrect.",
                "comments": "The independent conclusion agrees with original_correct = false.",
                "step_number": 4
              }
            ]
          },
          {
            "option": {
              "id": "D",
              "text": "The slope of f is 3."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: f(x) = 3x + 2 has the form f(x) = mx + b.",
                "comments": "Evidence: E1, source chunk 201.",
                "step_number": 1
              },
              {
                "step": "Parameter identification: m = 3.",
                "comments": "The coefficient of x is 3.",
                "step_number": 2
              },
              {
                "step": "Definition: m is the slope.",
                "comments": "Evidence: E5, source chunk 202.",
                "step_number": 3
              },
              {
                "step": "Conclusion: The slope is 3, so option D is correct.",
                "comments": "The independent conclusion agrees with original_correct = true.",
                "step_number": 4
              }
            ]
          }
        ]
      },
      "topic_relevence": {
        "relevent_to_topic": true,
        "confidence_in_judgement": 1.0,
        "reason": "The question directly requires evaluating a linear function and interpreting its slope, which is part of the supplied algebra/function topic."
      },
      "confidence_difficulty_relevence": {
        "bloom_level": {
          "current": "apply",
          "current_confidence": 0.97,
          "previous_confidence": 0.68
        },
        "task_difficulty": {
          "current": 2,
          "current_confidence": 0.96,
          "previous_confidence": null
        },
        "msq_difficulty": {
          "current": 2,
          "current_confidence": 0.96,
          "previous_confidence": null
        }
      }
    },
    {
      "id": "q_math_003",
      "stem": "Which of the following conditions imply that a square matrix A is invertible? Select all that apply.",
      "Source_validation": {
        "answerable": true,
        "evidence": "E1: A square matrix is invertible when there exists a matrix A^{-1} such that AA^{-1} = A^{-1}A = I. E2: A square matrix is invertible if and only if det(A) is nonzero. E3: A square matrix with two identical rows has determinant zero. These facts uniquely determine the truth value of every option.",
        "confidence": 0.99
      },
      "provenance": {
        "info_available": true,
        "relevent_chunks": [
          {
            "text": "A square matrix A is invertible if there exists a matrix A^{-1} such that AA^{-1} = A^{-1}A = I.",
            "id": 301
          },
          {
            "text": "For a square matrix, A is invertible if and only if det(A) != 0.",
            "id": 302
          },
          {
            "text": "If a square matrix has two identical rows, its determinant is zero.",
            "id": 303
          }
        ],
        "summary_info": "E1 establishes the definition of invertibility. E2 establishes the determinant criterion. E3 identifies a condition that prevents invertibility."
      },
      "answer_correctness": {
        "valid": true,
        "verified_correct_option_ids": [
          "A",
          "B",
          "D"
        ],
        "provided_correct_option_ids": [
          "A",
          "B",
          "D"
        ],
        "option_validations": [
          {
            "option": {
              "id": "A",
              "text": "There exists a matrix A^{-1} such that AA^{-1} = I."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: A matrix is invertible when it has a multiplicative inverse.",
                "comments": "Evidence: E1, source chunk 301.",
                "step_number": 1
              },
              {
                "step": "Condition: There exists A^{-1} such that AA^{-1} = A^{-1}A = I.",
                "comments": "Evidence: E1.",
                "step_number": 2
              },
              {
                "step": "Conclusion: Option A is a defining condition for invertibility.",
                "comments": "The conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "B",
              "text": "det(A) != 0."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: For a square matrix, invertibility is equivalent to a nonzero determinant.",
                "comments": "Evidence: E2, source chunk 302.",
                "step_number": 1
              },
              {
                "step": "Condition: det(A) != 0.",
                "comments": "This satisfies the sufficient and necessary determinant condition in E2.",
                "step_number": 2
              },
              {
                "step": "Conclusion: Option B is correct.",
                "comments": "The conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "C",
              "text": "det(A) = 0."
            },
            "original_correct": false,
            "valid": true,
            "independently_verified_correct": false,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: A square matrix is invertible if and only if det(A) != 0.",
                "comments": "Evidence: E2, source chunk 302.",
                "step_number": 1
              },
              {
                "step": "Comparison: det(A) = 0 contradicts the nonzero-determinant condition.",
                "comments": "Evidence: E2.",
                "step_number": 2
              },
              {
                "step": "Conclusion: Option C is incorrect.",
                "comments": "The independent conclusion agrees with original_correct = false.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "D",
              "text": "A has two identical rows."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Two identical rows imply det(A) = 0.",
                "comments": "Evidence: E3, source chunk 303.",
                "step_number": 1
              },
              {
                "step": "Comparison: det(A) = 0 implies A is not invertible.",
                "comments": "Evidence: E2, source chunk 302.",
                "step_number": 2
              },
              {
                "step": "Conclusion: Option D does not imply invertibility; therefore it should be classified as incorrect.",
                "comments": "This conflicts with original_correct = true. Therefore the option-level validity is actually false.",
                "step_number": 3
              }
            ]
          }
        ]
      },
      "topic_relevence": {
        "relevent_to_topic": true,
        "confidence_in_judgement": 1.0,
        "reason": "The question directly requires knowledge of matrix invertibility and determinants, which are core concepts of linear algebra."
      },
      "confidence_difficulty_relevence": {
        "bloom_level": {
          "current": "analyze",
          "current_confidence": 0.91,
          "previous_confidence": 0.74
        },
        "task_difficulty": {
          "current": 3,
          "current_confidence": 0.94,
          "previous_confidence": null
        },
        "msq_difficulty": {
          "current": 3,
          "current_confidence": 0.95,
          "previous_confidence": null
        }
      }
    }
  ]
}
```
### History:
```JSON
{
  "questions": [
    {
      "id": "q_history_001",
      "stem": "Which of the following were major causes of the French Revolution? Select all that apply.",
      "Source_validation": {
        "answerable": true,
        "evidence": "E1: France experienced a severe financial crisis caused by war debts and an inefficient taxation system. E2: French society was divided into unequal estates, with the Third Estate carrying much of the tax burden. E3: Enlightenment ideas promoted liberty, equality, and popular sovereignty. E4: The execution of Louis XVI occurred after the Revolution had already begun. These facts allow every option to be independently classified.",
        "confidence": 0.99
      },
      "provenance": {
        "info_available": true,
        "relevent_chunks": [
          {
            "text": "France faced severe financial difficulties due to war debts and an inefficient taxation system before the Revolution.",
            "id": 401
          },
          {
            "text": "French society was divided into three estates, and the Third Estate carried a disproportionate tax burden.",
            "id": 402
          },
          {
            "text": "Enlightenment thinkers promoted liberty, equality, and popular sovereignty.",
            "id": 403
          },
          {
            "text": "Louis XVI was executed after the Revolution had already begun.",
            "id": 404
          }
        ],
        "summary_info": "Chunks 401-403 support the major causal factors. Chunk 404 distinguishes a later revolutionary event from a cause preceding the outbreak."
      },
      "answer_correctness": {
        "valid": true,
        "verified_correct_option_ids": [
          "A",
          "B",
          "C"
        ],
        "provided_correct_option_ids": [
          "A",
          "B",
          "C"
        ],
        "option_validations": [
          {
            "option": {
              "id": "A",
              "text": "Financial crisis."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: France faced severe financial difficulties before the Revolution.",
                "comments": "Evidence: E1, source chunk 401.",
                "step_number": 1
              },
              {
                "step": "Cause: Financial crisis created serious economic and governmental pressure.",
                "comments": "Evidence: E1.",
                "step_number": 2
              },
              {
                "step": "Conclusion: Financial crisis is a valid contributing cause, so A is correct.",
                "comments": "The conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "B",
              "text": "Social inequality among the estates."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: French society was divided into unequal estates.",
                "comments": "Evidence: E2, source chunk 402.",
                "step_number": 1
              },
              {
                "step": "Consequence: The Third Estate carried a disproportionate tax burden.",
                "comments": "Evidence: E2.",
                "step_number": 2
              },
              {
                "step": "Conclusion: Social inequality was a major contributing cause, so B is correct.",
                "comments": "The conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "C",
              "text": "Enlightenment ideas."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Enlightenment thinkers promoted liberty, equality, and popular sovereignty.",
                "comments": "Evidence: E3, source chunk 403.",
                "step_number": 1
              },
              {
                "step": "Relation: These ideas challenged traditional political authority and influenced revolutionary thought.",
                "comments": "Evidence: E3.",
                "step_number": 2
              },
              {
                "step": "Conclusion: Enlightenment ideas contributed to the Revolution, so C is correct.",
                "comments": "The conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "D",
              "text": "The execution of Louis XVI before the Revolution began."
            },
            "original_correct": false,
            "valid": true,
            "independently_verified_correct": false,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Louis XVI was executed after the Revolution had already begun.",
                "comments": "Evidence: E4, source chunk 404.",
                "step_number": 1
              },
              {
                "step": "Chronological comparison: An event occurring after the beginning of the Revolution cannot be a cause occurring before its outbreak.",
                "comments": "Evidence: E4.",
                "step_number": 2
              },
              {
                "step": "Conclusion: D is incorrect as a cause of the outbreak.",
                "comments": "The independent conclusion agrees with original_correct = false.",
                "step_number": 3
              }
            ]
          }
        ]
      },
      "topic_relevence": {
        "relevent_to_topic": true,
        "confidence_in_judgement": 0.99,
        "reason": "The question directly requires understanding of the causes and chronology of the French Revolution."
      },
      "confidence_difficulty_relevence": {
        "bloom_level": {
          "current": "understand",
          "current_confidence": 0.94,
          "previous_confidence": null
        },
        "task_difficulty": {
          "current": 2,
          "current_confidence": 0.95,
          "previous_confidence": null
        },
        "msq_difficulty": {
          "current": 3,
          "current_confidence": 0.94,
          "previous_confidence": null
        }
      }
    },
    {
      "id": "q_history_002",
      "stem": "Which of the following were characteristics of the Roman Republic? Select all that apply.",
      "Source_validation": {
        "answerable": true,
        "evidence": "E1: Roman citizens elected magistrates. E2: The Senate was an important political institution. E3: Citizen assemblies voted on laws and elected officials. E4: The emperor was the defining head of the later Roman Empire rather than the Roman Republic. These facts permit complete classification of the options.",
        "confidence": 0.98
      },
      "provenance": {
        "info_available": true,
        "relevent_chunks": [
          {
            "text": "During the Roman Republic, citizens elected magistrates including consuls.",
            "id": 411
          },
          {
            "text": "The Senate was an influential political institution in the Roman Republic.",
            "id": 412
          },
          {
            "text": "Roman citizens participated in assemblies that voted on laws and elected officials.",
            "id": 413
          },
          {
            "text": "The Roman Empire developed later and was characterized by imperial rule.",
            "id": 414
          }
        ],
        "summary_info": "Chunks 411-413 identify Republican institutions. Chunk 414 provides the distinction needed to reject the imperial-rule option."
      },
      "answer_correctness": {
        "valid": true,
        "verified_correct_option_ids": [
          "A",
          "B",
          "C"
        ],
        "provided_correct_option_ids": [
          "A",
          "B",
          "C"
        ],
        "option_validations": [
          {
            "option": {
              "id": "A",
              "text": "Elected magistrates were part of the political system."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Roman citizens elected magistrates.",
                "comments": "Evidence: E1, source chunk 411.",
                "step_number": 1
              },
              {
                "step": "Conclusion: Elected magistrates were a characteristic of the Republic, so A is correct.",
                "comments": "The conclusion agrees with original_correct = true.",
                "step_number": 2
              }
            ]
          },
          {
            "option": {
              "id": "B",
              "text": "The Senate was an important political institution."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: The Senate was influential during the Roman Republic.",
                "comments": "Evidence: E2, source chunk 412.",
                "step_number": 1
              },
              {
                "step": "Conclusion: B is correct.",
                "comments": "The source directly supports the supplied classification.",
                "step_number": 2
              }
            ]
          },
          {
            "option": {
              "id": "C",
              "text": "Citizen assemblies participated in legislation and elections."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Citizens participated in assemblies.",
                "comments": "Evidence: E3, source chunk 413.",
                "step_number": 1
              },
              {
                "step": "Function: Assemblies voted on laws and elected officials.",
                "comments": "Evidence: E3.",
                "step_number": 2
              },
              {
                "step": "Conclusion: C is correct.",
                "comments": "The evidence supports the supplied correct=true classification.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "D",
              "text": "The Roman Republic was governed by an emperor as its defining head of state."
            },
            "original_correct": false,
            "valid": true,
            "independently_verified_correct": false,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Imperial rule characterizes the later Roman Empire.",
                "comments": "Evidence: E4, source chunk 414.",
                "step_number": 1
              },
              {
                "step": "Comparison: The Republic is characterized by institutions such as magistrates, the Senate, and assemblies.",
                "comments": "Evidence: E1, E2, and E3.",
                "step_number": 2
              },
              {
                "step": "Conclusion: D is incorrect.",
                "comments": "The supplied correct=false classification is supported.",
                "step_number": 3
              }
            ]
          }
        ]
      },
      "topic_relevence": {
        "relevent_to_topic": true,
        "confidence_in_judgement": 1.0,
        "reason": "The question directly examines the political structure of the Roman Republic."
      },
      "confidence_difficulty_relevence": {
        "bloom_level": {
          "current": "remember",
          "current_confidence": 0.98,
          "previous_confidence": null
        },
        "task_difficulty": {
          "current": 1,
          "current_confidence": 0.98,
          "previous_confidence": null
        },
        "msq_difficulty": {
          "current": 2,
          "current_confidence": 0.96,
          "previous_confidence": null
        }
      }
    },
    {
      "id": "q_history_003",
      "stem": "Which of the following contributed to the outbreak of World War I? Select all that apply.",
      "Source_validation": {
        "answerable": true,
        "evidence": "E1: European powers engaged in an arms race. E2: The alliance system divided Europe into opposing blocs. E3: Nationalism and imperial rivalry increased international tensions. E4: The assassination of Archduke Franz Ferdinand triggered the immediate diplomatic crisis. These pieces of evidence allow independent classification of each option.",
        "confidence": 0.99
      },
      "provenance": {
        "info_available": true,
        "relevent_chunks": [
          {
            "text": "European powers expanded their militaries and participated in an arms race before 1914.",
            "id": 421
          },
          {
            "text": "The alliance system divided Europe into opposing blocs and increased the possibility that a regional conflict would become a wider war.",
            "id": 422
          },
          {
            "text": "Nationalism and imperial competition heightened tensions among European powers.",
            "id": 423
          },
          {
            "text": "The assassination of Archduke Franz Ferdinand in Sarajevo triggered the immediate crisis that preceded the declaration of war.",
            "id": 424
          }
        ],
        "summary_info": "Chunks 421-424 provide evidence for militarism, alliances, nationalism, imperial competition, and the immediate trigger."
      },
      "answer_correctness": {
        "valid": true,
        "verified_correct_option_ids": [
          "A",
          "B",
          "C",
          "D"
        ],
        "provided_correct_option_ids": [
          "A",
          "B",
          "C",
          "D"
        ],
        "option_validations": [
          {
            "option": {
              "id": "A",
              "text": "Militarism."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: European powers expanded their militaries and participated in an arms race.",
                "comments": "Evidence: E1, source chunk 421.",
                "step_number": 1
              },
              {
                "step": "Historical relation: The arms race contributed to prewar international tension.",
                "comments": "Evidence: E1.",
                "step_number": 2
              },
              {
                "step": "Conclusion: A is correct.",
                "comments": "The conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "B",
              "text": "The alliance system."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Europe was divided into opposing alliance blocs.",
                "comments": "Evidence: E2, source chunk 422.",
                "step_number": 1
              },
              {
                "step": "Consequence: A regional conflict could expand into a wider war.",
                "comments": "Evidence: E2.",
                "step_number": 2
              },
              {
                "step": "Conclusion: B is correct.",
                "comments": "The source supports the supplied classification.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "C",
              "text": "Nationalism and imperial rivalry."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Nationalism and imperial competition increased tensions.",
                "comments": "Evidence: E3, source chunk 423.",
                "step_number": 1
              },
              {
                "step": "Conclusion: Both factors contributed to the unstable prewar environment.",
                "comments": "Evidence: E3.",
                "step_number": 2
              },
              {
                "step": "Final conclusion: C is correct.",
                "comments": "The independent conclusion agrees with original_correct = true.",
                "step_number": 3
              }
            ]
          },
          {
            "option": {
              "id": "D",
              "text": "The assassination of Archduke Franz Ferdinand."
            },
            "original_correct": true,
            "valid": true,
            "independently_verified_correct": true,
            "justification_correct": true,
            "proof": [
              {
                "step": "Known: Archduke Franz Ferdinand was assassinated in Sarajevo.",
                "comments": "Evidence: E4, source chunk 424.",
                "step_number": 1
              },
              {
                "step": "Causal relation: The assassination triggered the immediate diplomatic crisis preceding the war.",
                "comments": "Evidence: E4.",
                "step_number": 2
              },
              {
                "step": "Conclusion: D is correct as an immediate trigger.",
                "comments": "The source supports the supplied correct=true classification.",
                "step_number": 3
              }
            ]
          }
        ]
      },
      "topic_relevence": {
        "relevent_to_topic": true,
        "confidence_in_judgement": 0.99,
        "reason": "The question directly requires understanding of the causes and immediate trigger of World War I."
      },
      "confidence_difficulty_relevence": {
        "bloom_level": {
          "current": "analyze",
          "current_confidence": 0.92,
          "previous_confidence": 0.81
        },
        "task_difficulty": {
          "current": 3,
          "current_confidence": 0.93,
          "previous_confidence": null
        },
        "msq_difficulty": {
          "current": 3,
          "current_confidence": 0.96,
          "previous_confidence": null
        }
      }
    }
  ]
}

VERY IMPROTANT TO NOTE:
Question ids provided here are fake. the real ids you should EXTRACT them per question from the questions JSONs that has been provided to you from exactly the field `id`, which will have values (just an example) of the form: "q_d7ce3ee3598dab90038b9d6ab9f68a65"  
""".strip()