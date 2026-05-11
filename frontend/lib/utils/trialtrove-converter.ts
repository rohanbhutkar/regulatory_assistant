import type { ReferenceTrial } from '@/lib/types/study-types'
import type { TrialTroveTrial } from '@/lib/hooks/use-trialtrove-data'

export function convertTrialTroveToReferenceTrial(trialTrove: TrialTroveTrial): ReferenceTrial {
  // Extract NCT ID from Protocol/Trial ID field
  const nctId = trialTrove['Protocol/Trial ID']?.includes('NCT') 
    ? trialTrove['Protocol/Trial ID'].split('\n').find(id => id.includes('NCT')) || 'N/A'
    : 'N/A'

  // Extract locations from Countries field
  const locations = trialTrove['Countries'] ? trialTrove['Countries'].split(',').map(c => c.trim()) : []

  // Extract IE key points from inclusion criteria
  const ieKeyPoints = trialTrove['Inclusion Criteria'] 
    ? trialTrove['Inclusion Criteria'].split('\n').filter(line => line.trim().length > 0).slice(0, 5)
    : []

  return {
    id: `trial-${trialTrove['Trial ID']}`,
    nctId: nctId,
    title: trialTrove['Trial Title'] || 'Untitled Trial',
    indication: trialTrove['Disease'] || trialTrove['Therapeutic Area'] || 'Unknown',
    phase: trialTrove['Trial Phase'] || 'Unknown',
    primaryEndpoint: trialTrove['Primary Endpoint'] || trialTrove['Primary Endpoint Details'] || 'Not specified',
    ieKeyPoints,
    locations,
    sponsor: trialTrove['Sponsor/Collaborator'] || 'Unknown',
    selected: false,
    // Additional TrialTrove fields
    trialId: trialTrove['Trial ID'],
    protocolId: trialTrove['Protocol/Trial ID'],
    status: trialTrove['Trial Status'],
    therapeuticArea: trialTrove['Therapeutic Area'],
    disease: trialTrove['Disease'],
    patientSegment: trialTrove['Patient Segment'],
    meshTerm: trialTrove['MeSH Term'],
    icd10Code: trialTrove['Trial ICD-10 Code'],
    sponsorType: trialTrove['Sponsor/Collaborator Type'],
    sponsorCountry: trialTrove['Sponsor/Collaborator: Parent HQ Country'],
    primaryDrug: trialTrove['Primary Tested Drug'],
    drugMechanism: trialTrove['Primary Tested Drug: Mechanism Of Action'],
    drugTarget: trialTrove['Primary Tested Drug: Target'],
    drugClass: trialTrove['Primary Tested Drug: Therapeutic Class'],
    drugType: trialTrove['Primary Tested Drug: Drug Type'],
    trialObjective: trialTrove['Trial Objective'],
    primaryEndpointGroup: trialTrove['Primary Endpoint Group'],
    primaryEndpointDetails: trialTrove['Primary Endpoint Details'],
    secondaryEndpoints: trialTrove['Secondary/Other Endpoint'],
    secondaryEndpointGroup: trialTrove['Secondary/Other Endpoint Group'],
    secondaryEndpointDetails: trialTrove['Secondary/Other Endpoint Details'],
    startDate: trialTrove['Start Date'],
    enrollmentDuration: trialTrove['Enrollment Duration (Mos.)'],
    enrollmentCloseDate: trialTrove['Enrollment Close Date'],
    treatmentDuration: trialTrove['Treatment Duration (Mos.)'],
    primaryCompletionDate: trialTrove['Primary Completion Date'],
    fullCompletionDate: trialTrove['Full Completion Date'],
    ptsPerSitePerMonth: trialTrove['Pts/Site/Mo'],
    patientPopulation: trialTrove['Patient Population'],
    inclusionCriteria: trialTrove['Inclusion Criteria'],
    exclusionCriteria: trialTrove['Exclusion Criteria'],
    patientGender: trialTrove['Patient Gender'],
    patientAgeGroup: trialTrove['Patient Age Group'],
    minPatientAge: trialTrove['Min Patient Age'],
    maxPatientAge: trialTrove['Max Patient Age'],
    targetAccrual: trialTrove['Target Accrual'],
    actualAccrual: trialTrove['Actual Accrual (No. of patients)'],
    reportedSites: trialTrove['Reported Sites'],
    identifiedSites: trialTrove['Identified Sites'],
    trialRegion: trialTrove['Trial Region'],
    countries: trialTrove['Countries'],
    countriesCount: trialTrove['Countries Count'],
    treatmentPlan: trialTrove['Treatment Plan'],
    studyKeywords: trialTrove['Study Keywords'],
    studyDesign: trialTrove['Study Design'],
    trialResults: trialTrove['Trial Results'],
    trialNotes: trialTrove['Trial Notes'],
    associatedCRO: trialTrove['Associated CRO'],
    supportingUrls: trialTrove['Supporting URLs'],
    lastModifiedDate: trialTrove['Last Modified Date'],
    recordUrl: trialTrove['Record URL']
  }
}









