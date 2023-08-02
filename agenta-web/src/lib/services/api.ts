import useSWR from "swr"
import axios from "axios"
import {parseOpenApiSchema} from "@/lib/helpers/openapi_parser"
import {Variant, Parameter, EvaluationResponseType, Evaluation} from "@/lib/Types"
import {
    fromEvaluationResponseToEvaluation,
    fromEvaluationsRowsResponseToEvaluationsRows,
} from "../transformers"
import {EvaluationType} from "../enums"
/**
 * Raw interface for the parameters parsed from the openapi.json
 */

const fetcher = (...args) => fetch(...args).then((res) => res.json())

export async function fetchVariants(app: string): Promise<Variant[]> {
    const response = await axios.get(
        `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/app_variant/list_variants/?app_name=${app}`,
    )

    if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        return response.data.map((variant: Record<string, any>) => {
            let v: Variant = {
                variantName: variant.variant_name,
                templateVariantName: variant.previous_variant_name,
                persistent: true,
                parameters: variant.parameters,
            }
            return v
        })
    }

    return []
}

export function callVariant(
    inputParametersDict: Record<string, string>,
    optionalParameters: Parameter[],
    URIPath: string,
) {
    const inputParams = Object.keys(inputParametersDict).reduce((acc: any, key) => {
        acc[key] = inputParametersDict[key]
        return acc
    }, {})
    optionalParameters = optionalParameters || []

    const optParams = optionalParameters
        .filter((param) => param.default)
        .reduce((acc: any, param) => {
            acc[param.name] = param.default
            return acc
        }, {})

    const requestBody = {...inputParams, ...optParams}
    return axios
        .post(`${process.env.NEXT_PUBLIC_AGENTA_API_URL}/${URIPath}/generate`, requestBody, {
            headers: {
                accept: "application/json",
                "Content-Type": "application/json",
            },
        })
        .then((res) => {
            return res.data
        })
        .catch((error) => {
            if (error.response && error.response.status === 500) {
                throw new Error(error.response.data.error + " " + error.response.data.traceback)
            }
            if (error.response && error.response.status === 422) {
                throw new Error(
                    `Unprocessable Entity: The server understands the content type of the request, and the syntax of the request is correct, but it was unable to process the contained instructions. Data: ${JSON.stringify(
                        error.response.data,
                        null,
                        2,
                    )}`,
                )
            }
            throw error // If it's not a 500 status, or if error.response is undefined, rethrow the error so it can be handled elsewhere.
        })
}

/**
 * Parses the openapi.json from a variant and returns the parameters as an array of objects.
 * @param app
 * @param variantName
 * @returns
 */
export const getVariantParameters = async (app: string, variant: Variant) => {
    try {
        const sourceName = variant.templateVariantName
            ? variant.templateVariantName
            : variant.variantName
        const url = `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/${app}/${sourceName}/openapi.json`
        const response = await axios.get(url)
        const APIParams = parseOpenApiSchema(response.data)
        const initOptParams = APIParams.filter((param) => !param.input) // contains the default values too!
        const inputParams = APIParams.filter((param) => param.input) // don't have input values
        return {initOptParams, inputParams}
    } catch (error) {
        throw error
    }
}

/**
 * Saves a new variant to the database based on previous
 */
export async function saveNewVariant(appName: string, variant: Variant, parameters: Parameter[]) {
    const appVariant = {
        app_name: appName,
        variant_name: variant.templateVariantName,
    }
    console.log(
        parameters.reduce((acc, param) => {
            return {...acc, [param.name]: param.default}
        }, {}),
    )
    try {
        const response = await axios.post(
            `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/app_variant/add/from_previous/`,
            {
                previous_app_variant: appVariant,
                new_variant_name: variant.variantName,
                parameters: parameters.reduce((acc, param) => {
                    return {...acc, [param.name]: param.default}
                }, {}),
            },
        )

        // You can use the response here if needed
        console.log(response.data)
    } catch (error) {
        console.error(error)
        // Handle error here
        throw error
    }
}

export async function updateVariantParams(
    appName: string,
    variant: Variant,
    parameters: Parameter[],
) {
    try {
        const response = await axios.put(
            `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/app_variant/update_variant_parameters/`,
            {
                app_name: appName,
                variant_name: variant.variantName,
                parameters: parameters.reduce((acc, param) => {
                    return {...acc, [param.name]: param.default}
                }, {}),
            },
        )
    } catch (error) {
        console.error(error)
        throw error
    }
}

export async function removeApp(appName: string) {
    try {
        await axios.delete(
            `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/app_variant/remove_app/`,
            {data: {app_name: appName}},
        )
        console.log("App removed: " + appName)
    } catch (error) {
        console.error("Error removing " + appName + " " + error)
        throw error
    }
}

export async function removeVariant(appName: string, variantName: string) {
    try {
        await axios.delete(
            `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/app_variant/remove_variant/`,
            {data: {app_name: appName, variant_name: variantName}},
        )
        console.log("Variant removed: " + variantName)
    } catch (error) {
        console.error("Error removing " + variantName + " " + error)
        throw error
    }
}
/**
 * Loads the list of datasets
 * @returns
 */
export const useLoadDatasetsList = (app_name: string) => {
    const {data, error} = useSWR(
        `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/datasets?app_name=${app_name}`,
        fetcher,
    )
    return {
        datasets: data,
        isDatasetsLoading: !error && !data,
        isDatasetsLoadingError: error,
    }
}

export async function createNewTestSet(appName: string, testSetName: string, testSetData: any) {
    try {
        const response = await axios.post(
            `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/datasets/${appName}`,
            {
                name: testSetName,
                csvdata: testSetData,
            },
        )
        return response
    } catch (error) {
        console.error(error)
        throw error
    }
}

export async function updateTestSet(testSetId: String, testSetName: string, testSetData: any) {
    try {
        const response = await axios.put(
            `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/datasets/${testSetId}`,
            {
                name: testSetName,
                csvdata: testSetData,
            },
        )
        return response
    } catch (error) {
        console.error(error)
        throw error
    }
}

export const loadDataset = async (datasetId: string) => {
    return fetch(`${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/datasets/${datasetId}`, {
        headers: {
            "Content-Type": "application/json",
        },
    })
        .then((res) => res.json())
        .then((data) => {
            return data
        })
        .catch((err) => {
            console.error(err)
        })
}

export const deleteDatasets = async (ids: string[]) => {
    try {
        const response = await axios({
            method: "delete",
            url: `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/datasets`,
            data: {dataset_ids: ids},
        })
        if (response.status === 200) {
            return response.data
        }
    } catch (error) {
        console.error(`Error deleting entity: ${error}`)
        throw error
    }
}

const eval_endpoint = axios.create({
    baseURL: `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/evaluations`,
})

export const loadEvaluations = async (app_name: string) => {
    try {
        return await eval_endpoint.get(`?app_name=${app_name}`).then((responseData) => {
            const evaluations = responseData.data.map((item: EvaluationResponseType) => {
                return fromEvaluationResponseToEvaluation(item)
            })

            return evaluations
        })
    } catch (error) {
        console.error(error)
        throw error
    }
}

export const loadEvaluation = async (evaluationId: string) => {
    try {
        return await eval_endpoint.get(evaluationId).then((responseData) => {
            return fromEvaluationResponseToEvaluation(responseData.data)
        })
    } catch (error) {
        console.error(error)
        throw error
    }
}

export const deleteEvaluations = async (ids: string[]) => {
    try {
        const response = await axios({
            method: "delete",
            url: `${process.env.NEXT_PUBLIC_AGENTA_API_URL}/api/evaluations`,
            data: {evaluations_ids: ids},
        })
        if (response.status === 200) {
            return response.data
        }
    } catch (error) {
        console.error(`Error deleting entity: ${error}`)
        throw error
    }
}

export const loadEvaluationsRows = async (
    evaluationTableId: string,
    evaluation: Evaluation,
) => {
    try {
        return await eval_endpoint
            .get(`${evaluationTableId}/evaluation_rows`)
            .then((responseData) => {
                const evaluationsRows = responseData.data.map((item: any) => {
                    return fromEvaluationsRowsResponseToEvaluationsRows(item, evaluation)
                })

                return evaluationsRows
            })
    } catch (error) {
        console.error(error)
        throw error
    }
}

export const updateEvaluations = async (evaluationTableId: string, data) => {
    const response = await eval_endpoint.put(`${evaluationTableId}`, data)
    return response.data
}

export const updateEvaluationRow = async (
    evaluationTableId: string,
    evaluationRowId: string,
    data,
    evaluationType: EvaluationType,
) => {
    const response = await eval_endpoint.put(
        `${evaluationTableId}/evaluation_row/${evaluationRowId}/${evaluationType}`,
        data,
    )
    return response.data
}

export const postEvaluationRow = async (evaluationTableId: string, data) => {
    const response = await eval_endpoint.post(`${evaluationTableId}/evaluation_row`, data)
    return response.data
}
