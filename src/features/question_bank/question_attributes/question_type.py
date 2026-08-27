from enum import Enum
from .constants import MSQ_TEXT, MSQ_SCHEMA,MSQ_BLOOM_LEVELS
class QuestionType(Enum):
    MSQ = (1,MSQ_TEXT,MSQ_SCHEMA,MSQ_BLOOM_LEVELS)