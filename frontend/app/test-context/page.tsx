"use client"

// Test page to verify StudyDesigner context is working
import React from 'react'
import { StudyDesignerProvider, useStudyDesigner } from '@/lib/contexts/study-designer-context'

function TestComponent() {
  const { agentActions, activeTab } = useStudyDesigner()
  
  return (
    <div>
      <h1>Context Test</h1>
      <p>Active Tab: {activeTab}</p>
      <p>Agent Actions Available: {agentActions ? 'Yes' : 'No'}</p>
      <button onClick={() => agentActions?.selectTrials('NSCLC')}>
        Test Select Trials
      </button>
    </div>
  )
}

export default function TestPage() {
  return (
    <StudyDesignerProvider>
      <TestComponent />
    </StudyDesignerProvider>
  )
}
