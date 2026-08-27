from .question_difficulty import(
CognitiveComplexity,KnowlegeComplexity,BLOOM_FRAMEWORK_TEXT,PER_LEVEL_GENERAL_RULES,HardnessPerLevel
)
from .question_type import QuestionType

MSQ_PROMPT=f"""
Generate this amount of questions:
per an MSQ level (as we have three levels) generate:
80 {CognitiveComplexity.REMEMBER.name} questions distributed like the following:
10 questions for REMEMBER: difficulty level 1
10 questions for REMEMBER: difficulty level 2
30 questions for REMEMBER: difficulty level 3
20 questions for REMEMBER: difficulty level 4
10 questions for REMEMBER: difficulty level 5
80 {CognitiveComplexity.UNDERSTAND.name} questions distributed like the following:
10 questions for UNDERSTAND: difficulty level 1
10 questions for UNDERSTAND: difficulty level 2
30 questions for UNDERSTAND: difficulty level 3
20 questions for UNDERSTAND: difficulty level 4
10 questions for UNDERSTAND: difficulty level 5
80 {CognitiveComplexity.APPLY.name} questions distributed like the following:
10 questions for APPLY: difficulty level 1
10 questions for APPLY: difficulty level 2
30 questions for APPLY: difficulty level 3
20 questions for APPLY: difficulty level 4
10 questions for APPLY: difficulty level 5
80 {CognitiveComplexity.ANALYZE.name} questions distributed like the following:
10 questions for ANALYZE: difficulty level 1
10 questions for ANALYZE: difficulty level 2
30 questions for ANALYZE: difficulty level 3
20 questions for ANALYZE: difficulty level 4
10 questions for ANALYZE: difficulty level 5

----->>>>> here are all the definitions, explanations and guidance for creating such questions correctly into correct output JSON format:
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

---->>>>> now explanation about question type, the rules, format & structure to follow:
{QuestionType.MSQ.value[1]}
{QuestionType.MSQ.value[2]}
{QuestionType.MSQ.value[3]}
""".strip()



