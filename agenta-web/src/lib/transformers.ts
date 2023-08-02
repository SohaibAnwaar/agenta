import {Evaluation, EvaluationResponseType, Variant} from "./Types"
import {EvaluationType} from "./enums"
import {formatDate} from "./helpers/dateTimeHelper"

export const fromEvaluationResponseToEvaluation = (item: EvaluationResponseType) => {
    const variants: Variant[] = item.variants.map((variantName: string) => {
        const variant: Variant = {
            variantName: variantName,
            templateVariantName: null,
            persistent: true,
            parameters: null,
        }
        return variant
    })

    let evaluationTypeSettings = {}
    if (item.evaluation_type_settings?.similarity_threshold) {
        evaluationTypeSettings["similarityThreshold"] =
            item.evaluation_type_settings.similarity_threshold
    }

    return {
        id: item.id,
        createdAt: formatDate(item.created_at),
        variants: variants,
        dataset: item.dataset,
        appName: item.app_name,
        status: item.status,
        evaluationType: item.evaluation_type,
        evaluationTypeSettings: evaluationTypeSettings,
    }
}

export const fromEvaluationsRowsResponseToEvaluationsRows = (
    item: any,
    evaluation: Evaluation,
) => {
    let evaluationRow = {
        id: item.id,
        inputs: item.inputs,
        outputs: item.outputs,
        vote: item.vote,
        correctAnswer: item.correct_answer,
    }

    if (evaluation.evaluationType === EvaluationType.human_a_b_testing) {
        evaluationRow = {...evaluationRow, vote: item.vote}
    } else if (
        evaluation.evaluationType === EvaluationType.auto_exact_match ||
        evaluation.evaluationType === EvaluationType.auto_similarity_match
    ) {
        evaluationRow = {...evaluationRow, score: item.score}
    }
    return evaluationRow
}
