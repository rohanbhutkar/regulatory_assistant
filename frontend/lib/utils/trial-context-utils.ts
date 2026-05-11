/**
 * Utility functions for extracting context from trial data
 */

export interface TrialData {
  indication?: string
  Disease?: string
  phase?: string
  Trial_Phase?: string
  therapeuticArea?: string
  Therapeutic_Area?: string
  [key: string]: any
}

/**
 * Extract the most common indication from a list of trials
 * This ensures we use trial-specific data rather than global context
 */
export function extractIndicationFromTrials(trials: TrialData[], fallback: string = ""): string {
  if (!trials || trials.length === 0) return fallback
  
  // Get all unique indications from trials
  const indications = trials
    .map(t => t.indication || t.Disease)
    .filter(Boolean) as string[]
  
  if (indications.length === 0) return fallback
  
  // Find the most common indication
  const indicationCounts = indications.reduce((acc, ind) => {
    acc[ind] = (acc[ind] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  
  const mostCommon = Object.entries(indicationCounts)
    .sort((a, b) => b[1] - a[1])[0]?.[0]
  
  return mostCommon || fallback
}

/**
 * Extract the most common phase from a list of trials
 */
export function extractPhaseFromTrials(trials: TrialData[], fallback: string = ""): string {
  if (!trials || trials.length === 0) return fallback
  
  // Get all unique phases from trials
  const phases = trials
    .map(t => t.phase || t.Trial_Phase)
    .filter(Boolean) as string[]
  
  if (phases.length === 0) return fallback
  
  // Find the most common phase
  const phaseCounts = phases.reduce((acc, p) => {
    acc[p] = (acc[p] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  
  const mostCommon = Object.entries(phaseCounts)
    .sort((a, b) => b[1] - a[1])[0]?.[0]
  
  return mostCommon || fallback
}

/**
 * Extract the most common therapeutic area from a list of trials
 */
export function extractTherapeuticAreaFromTrials(trials: TrialData[], fallback: string = ""): string {
  if (!trials || trials.length === 0) return fallback
  
  // Get all unique therapeutic areas from trials
  const areas = trials
    .map(t => t.therapeuticArea || t.Therapeutic_Area)
    .filter(Boolean) as string[]
  
  if (areas.length === 0) return fallback
  
  // Find the most common therapeutic area
  const areaCounts = areas.reduce((acc, area) => {
    acc[area] = (acc[area] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  
  const mostCommon = Object.entries(areaCounts)
    .sort((a, b) => b[1] - a[1])[0]?.[0]
  
  return mostCommon || fallback
}

/**
 * Extract comprehensive reference info from trials
 * Returns a formatted string with indication, phase, and therapeutic area
 */
export function extractReferenceInfoFromTrials(trials: TrialData[], globalContext?: {
  indication?: string
  phase?: string
  therapeuticArea?: string
}): string {
  const indication = extractIndicationFromTrials(trials, globalContext?.indication)
  const phase = extractPhaseFromTrials(trials, globalContext?.phase)
  const therapeuticArea = extractTherapeuticAreaFromTrials(trials, globalContext?.therapeuticArea)
  
  const parts: string[] = []
  if (phase) parts.push(phase.startsWith('Phase') ? phase : `Phase ${phase}`)
  if (indication) parts.push(indication)
  if (therapeuticArea && therapeuticArea !== indication) parts.push(`(${therapeuticArea})`)
  
  return parts.join(' ') || globalContext?.indication || ''
}




