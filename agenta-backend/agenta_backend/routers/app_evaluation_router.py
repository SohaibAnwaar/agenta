from fastapi import HTTPException, APIRouter, Body
from agenta_backend.models.api.evaluation_model import Evaluation, EvaluationRow, EvaluationRowUpdate, NewEvaluation, DeleteEvaluation, EvaluationType
from agenta_backend.services.db_mongo import evaluations, evaluation_rows, datasets
from datetime import datetime
from bson import ObjectId
from typing import List, Optional
router = APIRouter()


@router.post("/", response_model=Evaluation)
async def create_evaluation(newEvaluationData: NewEvaluation = Body(...)):
    """Creates a new comparison table document

    Raises:
        HTTPException: _description_

    Returns:
        _description_
    """
    evaluation = newEvaluationData.dict()
    evaluation["created_at"] = evaluation["updated_at"] = datetime.utcnow()

    newEvaluation = await evaluations.insert_one(evaluation)

    if newEvaluation.acknowledged:
        datasetId = evaluation["dataset"]["_id"]
        dataset = await datasets.find_one({"_id": ObjectId(datasetId)})
        csvdata = dataset["csvdata"]
        for datum in csvdata:
            evaluation_row = {
                "evaluation_id": str(newEvaluation.inserted_id),
                "inputs": [{'input_name': name, 'input_value': datum[name]} for name in evaluation["inputs"]],
                "outputs": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            if newEvaluationData.evaluation_type == EvaluationType.auto_exact_match:
                evaluation_row["score"] = ""
                if "correct_answer" in datum:
                    evaluation_row["correct_answer"] = datum["correct_answer"]

            if newEvaluationData.evaluation_type == EvaluationType.auto_similarity_match:
                evaluation_row["score"] = ""
                if "correct_answer" in datum:
                    evaluation_row["correct_answer"] = datum["correct_answer"]

            if newEvaluationData.evaluation_type == EvaluationType.human_a_b_testing:
                evaluation_row["vote"] = ""


            await evaluation_rows.insert_one(evaluation_row)

        evaluation["id"] = str(newEvaluation.inserted_id)
        return evaluation
    else:
        raise HTTPException(status_code=500, detail="Failed to create evaluation_row")

@router.get("/{evaluation_id}/evaluation_rows", response_model=List[EvaluationRow])
async def fetch_evaluation_rows(evaluation_id: str):
    """Creates an empty evaluation row

    Arguments:
        evaluation_row -- _description_

    Raises:
        HTTPException: _description_

    Returns:
        _description_
    """
    cursor = evaluation_rows.find({"evaluation_id": evaluation_id})
    items = await cursor.to_list(length=100)    # limit length to 100 for the example
    for item in items:
        item['id'] = str(item['_id'])
    return items

@router.post("/{evaluation_id}/evaluation_row", response_model=EvaluationRow)
async def create_evaluation_row(evaluation_row: EvaluationRow):
    """Creates an empty evaluation row

    Arguments:
        evaluation_row -- _description_

    Raises:
        HTTPException: _description_

    Returns:
        _description_
    """
    evaluation_row_dict = evaluation_row.dict()
    evaluation_row_dict.pop("id", None)

    evaluation_row_dict["created_at"] = evaluation_row_dict["updated_at"] = datetime.utcnow()
    result = await evaluation_rows.insert_one(evaluation_row_dict)
    if result.acknowledged:
        evaluation_row_dict["id"] = str(result.inserted_id)
        return evaluation_row_dict
    else:
        raise HTTPException(status_code=500, detail="Failed to create evaluation_row")


@router.put("/{evaluation_id}/evaluation_row/{evaluation_row_id}/{evaluation_type}")
async def update_evaluation_row(evaluation_row_id: str, evaluation_row: EvaluationRowUpdate, evaluation_type: EvaluationType):
    """Updates an evaluation row with a vote

    Arguments:
        evaluation_row_id -- _description_
        evaluation_row -- _description_

    Raises:
        HTTPException: _description_

    Returns:
        _description_
    """
    evaluation_row_dict = evaluation_row.dict()
    evaluation_row_dict["updated_at"] = datetime.utcnow()

    new_evaluation_set = {
        'outputs': evaluation_row_dict["outputs"]
    }

    if (evaluation_type == EvaluationType.auto_exact_match or
        evaluation_type == EvaluationType.auto_similarity_match):
        new_evaluation_set["score"] = evaluation_row_dict["score"]
    elif evaluation_type == EvaluationType.human_a_b_testing:
        new_evaluation_set["vote"] = evaluation_row_dict["vote"]

    result = await evaluation_rows.update_one(
        {'_id': ObjectId(evaluation_row_id)},
        {'$set': new_evaluation_set}
    )
    if result.acknowledged:
        return evaluation_row_dict
    else:
        raise HTTPException(status_code=500, detail="Failed to create evaluation_row")


@router.get("/", response_model=List[Evaluation])
async def fetch_list_evaluations(app_name: Optional[str] = None):
    """lists of all comparison tables

    Returns:
        _description_
    """
    cursor = evaluations.find({"app_name": app_name}).sort('created_at', -1)
    items = await cursor.to_list(length=100)    # limit length to 100 for the example
    for item in items:
        item['id'] = str(item['_id'])
    return items


@router.get("/{evaluation_id}", response_model=Evaluation)
async def fetch_evaluation(evaluation_id: str):
    """Fetch one comparison table

    Returns:
        _description_
    """
    evaluation = await evaluations.find_one({"_id" : ObjectId(evaluation_id)})
    if evaluation:
        evaluation["id"] = str(evaluation["_id"])
        return evaluation
    else:
        raise HTTPException(status_code=404, detail=f"dataset with id {evaluation_id} not found")

@router.delete("/", response_model=List[str])
async def delete_evaluations(delete_evaluations: DeleteEvaluation):
    """
    Delete specific comparison tables based on their unique IDs.

    Args:
    delete_evaluations (List[str]): The unique identifiers of the comparison tables to delete.

    Returns:
    A list of the deleted comparison tables' IDs.
    """
    deleted_ids = []

    for evaluations_id in delete_evaluations.evaluations_ids:
        evaluation = await evaluations.find_one({'_id': ObjectId(evaluations_id)})

        if evaluation is not None:
            result = await evaluations.delete_one({'_id': ObjectId(evaluations_id)})
            if result:
                deleted_ids.append(evaluations_id)
        else:
            raise HTTPException(status_code=404, detail=f"Comparison table {evaluations_id} not found")

    return deleted_ids

@router.get("/{evaluation_id}/results")
async def fetch_results(evaluation_id: str):
    """Fetch all the results for one the comparison table

    Arguments:
        evaluation_id -- _description_

    Returns:
        _description_
    """
    evaluation = await evaluations.find_one({"_id": ObjectId(evaluation_id)})

    if (evaluation["evaluation_type"]== EvaluationType.human_a_b_testing):
        results = await fetch_results_for_human_a_b_testing_evaluation(evaluation_id, evaluation.get("variants", []))
        # TODO: replace votes_data by results_data
        return {"votes_data": results}

    elif (evaluation["evaluation_type"]== EvaluationType.auto_exact_match):
        results = await fetch_results_for_auto_exact_match_evaluation(evaluation_id, evaluation.get("variant", []))
        return {"scores_data": results}

    elif (evaluation["evaluation_type"]== EvaluationType.auto_similarity_match):
        results = await fetch_results_for_auto_similarity_match_evaluation(evaluation_id, evaluation.get("variant", []))
        return {"scores_data": results}

async def fetch_results_for_human_a_b_testing_evaluation(evaluation_id: str, variants: list):
    results = {}
    evaluation_rows_nb = await evaluation_rows.count_documents({
        'evaluation_id': evaluation_id,
        'vote': {'$ne': ''}
    })

    if evaluation_rows_nb == 0:
        return results

    results["variants"] = variants
    results["variants_votes_data"] = {}
    results["nb_of_rows"] = evaluation_rows_nb

    flag_votes_nb = await evaluation_rows.count_documents({
        'vote': '0',
        'evaluation_id': evaluation_id
    })
    results["flag_votes"] = {}
    results["flag_votes"]["number_of_votes"] = flag_votes_nb
    results["flag_votes"]["percentage"] = round(flag_votes_nb / evaluation_rows_nb * 100, 2) if evaluation_rows_nb else 0

    for item in variants:
        results["variants_votes_data"][item] = {}
        variant_votes_nb: int = await evaluation_rows.count_documents({
            'vote': item,
            'evaluation_id': evaluation_id
        })
        results["variants_votes_data"][item]["number_of_votes"]= variant_votes_nb
        results["variants_votes_data"][item]["percentage"] = round(variant_votes_nb / evaluation_rows_nb * 100, 2) if evaluation_rows_nb else 0
    return results

async def fetch_results_for_auto_exact_match_evaluation(evaluation_id: str, variant: str):
    results = {}
    evaluation_rows_nb = await evaluation_rows.count_documents({
        'evaluation_id': evaluation_id,
        'score': {'$ne': ''}
    })

    if evaluation_rows_nb == 0:
        return results

    results["variant"] = variant
    # results["variants_scores_data"] = {}
    results["nb_of_rows"] = evaluation_rows_nb

    correct_scores_nb: int = await evaluation_rows.count_documents({
        'score': 'correct',
        'evaluation_id': evaluation_id
    })

    wrong_scores_nb: int = await evaluation_rows.count_documents({
        'score': 'wrong',
        'evaluation_id': evaluation_id
    })
    results["scores"] = {}
    results["scores"]["correct"] = correct_scores_nb
    results["scores"]["wrong"] = wrong_scores_nb
    return results

async def fetch_results_for_auto_similarity_match_evaluation(evaluation_id: str, variant: str):
    results = {}
    evaluation_rows_nb = await evaluation_rows.count_documents({
        'evaluation_id': evaluation_id,
        'score': {'$ne': ''}
    })

    if evaluation_rows_nb == 0:
        return results

    results["variant"] = variant
    results["nb_of_rows"] = evaluation_rows_nb

    similar_scores_nb: int = await evaluation_rows.count_documents({
        'score': 'true',
        'evaluation_id': evaluation_id
    })

    dissimilar_scores_nb: int = await evaluation_rows.count_documents({
        'score': 'false',
        'evaluation_id': evaluation_id
    })
    results["scores"] = {}
    results["scores"]["true"] = similar_scores_nb
    results["scores"]["false"] = dissimilar_scores_nb
    return results
