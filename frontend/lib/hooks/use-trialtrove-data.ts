import { useState, useEffect } from 'react'

export interface TrialTroveTrial {
  'Trial ID': number
  'Protocol/Trial ID': string
  'Trial Title': string
  'Trial Phase': string
  'Trial Status': string
  'Therapeutic Area': string
  'Disease': string
  'Patient Segment': string
  'MeSH Term': string
  'Trial ICD-10 Code': string
  'Record Type': string
  'Sponsor/Collaborator': string
  'Sponsor/Collaborator Role': string
  'Sponsor/Collaborator Type': string
  'Sponsor/Collaborator: Parent HQ Country': string
  'Sponsor/Collaborator: Parent HQ State': string | null
  'Sponsor/Collaborator: Parent HQ City': string | null
  'Sponsor/Collaborator: Parent HQ Postal Code': string | null
  'Primary Tested Drug': string
  'Primary Tested Drug: Mechanism Of Action': string
  'Primary Tested Drug: Target': string
  'Primary Tested Drug: Therapeutic Class': string
  'Primary Tested Drug: Drug Type': string
  'Other Tested Drug': string | null
  'Other Tested Drug: Mechanism Of Action': string | null
  'Other Tested Drug: Target': string | null
  'Other Tested Drug: Therapeutic Class': string | null
  'Other Tested Drug: Drug Type': string | null
  'Oncology Biomarker': string | null
  'Oncology Biomarker Common Use(s)': string | null
  'Trial Objective': string
  'Primary Endpoint': string | null
  'Primary Endpoint Group': string | null
  'Primary Endpoint Details': string | null
  'Secondary/Other Endpoint': string
  'Secondary/Other Endpoint Group': string
  'Secondary/Other Endpoint Details': string
  'Start Date': string
  'Start Date Type': string
  'Enrollment Duration (Mos.)': number
  'Enrollment Duration Type': string
  'Enrollment Close Date': string
  'Enrollment Close Date Type': string
  'Treatment Duration (Mos.)': number
  'Treatment Duration Type': string
  'Primary Completion Date': string
  'Primary Completion Date Type': string
  'Full Completion Date': string | null
  'Full Completion Date Type': string | null
  'Primary Endpoints Reported Date': string | null
  'Primary Endpoints Reported Date Type': string | null
  'Pts/Site/Mo': number
  'Pts/Site/Mo Type': string
  'Patient Population': string
  'Inclusion Criteria': string
  'Exclusion Criteria': string
  'Patient Gender': string
  'Patient Age Group': string
  'Min Patient Age': number
  'Min Patient Age Unit': string
  'Max Patient Age': number | null
  'Max Patient Age Unit': string | null
  'Target Accrual': number | null
  'Actual Accrual (No. of patients)': number | null
  'Actual Accrual (% of Target)': number | null
  'Reported Sites': number | null
  'Identified Sites': number | null
  'Trial Region': string
  'Countries': string
  'Countries Count': number | null
  'ClinicalTrials.gov Location Country': string | null
  'ClinicalTrials.gov Sites Count': string | null
  'Disposition of Patients': string | null
  'Prior/Concurrent Therapy': string | null
  'Treatment Plan': string
  'Study Keywords': string
  'Study Design': string
  'Trial Results': string | null
  'Trial Notes': string | null
  'Trial Tag/Attribute': string | null
  'Decentralized (DCT) Attributes': string | null
  'Trial Outcomes': string | null
  'Outcome Details': string | null
  'Associated CRO': string | null
  'Supporting URLs': string
  'Last Modified Date': string
  'Last Full Review': string
  'Record URL': string
}

export interface TrialTroveResponse {
  trials: TrialTroveTrial[]
  total_count: number
  query: string
  limit: number
}

export function useTrialTroveData(query: string = '', limit: number = 1000) {
  const [data, setData] = useState<TrialTroveTrial[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [totalCount, setTotalCount] = useState(0)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      
      try {
        const url = new URL('http://127.0.0.1:8001/api/data/trialtrove')
        if (query) url.searchParams.set('query', query)
        url.searchParams.set('limit', limit.toString())
        
        const response = await fetch(url.toString())
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const result: TrialTroveResponse = await response.json()
        setData(result.trials)
        setTotalCount(result.total_count)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred')
        console.error('Error fetching TrialTrove data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [query, limit])

  return { data, loading, error, totalCount }
}


export interface TrialTroveTrial {
  'Trial ID': number
  'Protocol/Trial ID': string
  'Trial Title': string
  'Trial Phase': string
  'Trial Status': string
  'Therapeutic Area': string
  'Disease': string
  'Patient Segment': string
  'MeSH Term': string
  'Trial ICD-10 Code': string
  'Record Type': string
  'Sponsor/Collaborator': string
  'Sponsor/Collaborator Role': string
  'Sponsor/Collaborator Type': string
  'Sponsor/Collaborator: Parent HQ Country': string
  'Sponsor/Collaborator: Parent HQ State': string | null
  'Sponsor/Collaborator: Parent HQ City': string | null
  'Sponsor/Collaborator: Parent HQ Postal Code': string | null
  'Primary Tested Drug': string
  'Primary Tested Drug: Mechanism Of Action': string
  'Primary Tested Drug: Target': string
  'Primary Tested Drug: Therapeutic Class': string
  'Primary Tested Drug: Drug Type': string
  'Other Tested Drug': string | null
  'Other Tested Drug: Mechanism Of Action': string | null
  'Other Tested Drug: Target': string | null
  'Other Tested Drug: Therapeutic Class': string | null
  'Other Tested Drug: Drug Type': string | null
  'Oncology Biomarker': string | null
  'Oncology Biomarker Common Use(s)': string | null
  'Trial Objective': string
  'Primary Endpoint': string | null
  'Primary Endpoint Group': string | null
  'Primary Endpoint Details': string | null
  'Secondary/Other Endpoint': string
  'Secondary/Other Endpoint Group': string
  'Secondary/Other Endpoint Details': string
  'Start Date': string
  'Start Date Type': string
  'Enrollment Duration (Mos.)': number
  'Enrollment Duration Type': string
  'Enrollment Close Date': string
  'Enrollment Close Date Type': string
  'Treatment Duration (Mos.)': number
  'Treatment Duration Type': string
  'Primary Completion Date': string
  'Primary Completion Date Type': string
  'Full Completion Date': string | null
  'Full Completion Date Type': string | null
  'Primary Endpoints Reported Date': string | null
  'Primary Endpoints Reported Date Type': string | null
  'Pts/Site/Mo': number
  'Pts/Site/Mo Type': string
  'Patient Population': string
  'Inclusion Criteria': string
  'Exclusion Criteria': string
  'Patient Gender': string
  'Patient Age Group': string
  'Min Patient Age': number
  'Min Patient Age Unit': string
  'Max Patient Age': number | null
  'Max Patient Age Unit': string | null
  'Target Accrual': number | null
  'Actual Accrual (No. of patients)': number | null
  'Actual Accrual (% of Target)': number | null
  'Reported Sites': number | null
  'Identified Sites': number | null
  'Trial Region': string
  'Countries': string
  'Countries Count': number | null
  'ClinicalTrials.gov Location Country': string | null
  'ClinicalTrials.gov Sites Count': string | null
  'Disposition of Patients': string | null
  'Prior/Concurrent Therapy': string | null
  'Treatment Plan': string
  'Study Keywords': string
  'Study Design': string
  'Trial Results': string | null
  'Trial Notes': string | null
  'Trial Tag/Attribute': string | null
  'Decentralized (DCT) Attributes': string | null
  'Trial Outcomes': string | null
  'Outcome Details': string | null
  'Associated CRO': string | null
  'Supporting URLs': string
  'Last Modified Date': string
  'Last Full Review': string
  'Record URL': string
}

export interface TrialTroveResponse {
  trials: TrialTroveTrial[]
  total_count: number
  query: string
  limit: number
}










