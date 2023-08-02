from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

# evaluationTypes = ["evaluation"]
class EvaluationTypeSettings(BaseModel):
    similarity_threshold: Optional[float]

class EvaluationType(str, Enum):
    auto_exact_match = "auto_exact_match"
    auto_similarity_match = "auto_similarity_match"
    auto_ai_critique = "auto_ai_critique"
    human_a_b_testing = "human_a_b_testing"
    human_scoring = "human_scoring"

class Evaluation(BaseModel):
    id: str
    status: str
    evaluation_type: EvaluationType
    evaluation_type_settings: Optional[EvaluationTypeSettings]
    variants: Optional[List[str]]
    app_name: str
    dataset: Dict[str, str] = Field(...)
    created_at: datetime
    updated_at: datetime


class EvaluationRowInput(BaseModel):
    input_name: str
    input_value: str


class EvaluationRowOutput(BaseModel):
    variant_name: str
    variant_output: str


class EvaluationRow(BaseModel):
    evaluation_id: str
    inputs: List[EvaluationRowInput]
    outputs: List[EvaluationRowOutput]
    vote: Optional[str]
    score: Optional[str]
    correct_answer: Optional[str]
    id: Optional[str]


class EvaluationRowUpdate(BaseModel):
    vote: Optional[str]
    score: Optional[str]
    outputs: List[EvaluationRowOutput]

class NewEvaluation(BaseModel):
    evaluation_type: EvaluationType
    evaluation_type_settings: Optional[EvaluationTypeSettings]
    app_name: str
    variants: List[str]
    inputs: List[str]
    dataset: Dict[str, str] = Field(...)
    status: str = Field(...)


class DeleteEvaluation(BaseModel):
    evaluations_ids: List[str]
