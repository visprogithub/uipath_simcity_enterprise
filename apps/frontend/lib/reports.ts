export interface AfterActionReport {
  reportId: string
  generatedAt: number
  scenarioId: string
  durationTicks: number
  durationSeconds: number
  executiveSummary: string
  outcomeStatus: 'recovered' | 'degraded'
  phaseTimeline: { tick: number; phase: string }[]
  worstPhaseReached: string
  metrics: {
    start: Record<string, number>
    worst: Record<string, number>
    end: Record<string, number>
    recoveryRatePerTick: number
  }
  mostAffectedBuildings: {
    buildingId: string
    name: string
    minHealth: number
    currentHealth: number
    recoveryTick: number | null
  }[]
  critisTicks: number
  estimatedCrisisWithoutAutomation: number
  automationContributionPct: number
  playerInterventionCount: number
  agentInterventionCount: number
  effectiveInterventions: {
    tick: number
    source: string
    actionType: string
    description: string
    stabilityDelta: number
    targetBuilding: string | null
  }[]
  uipathJobs: {
    jobId: string
    processName: string
    triggeredAtTick: number
    triggeredBy: string
    state: string
    stabilityImpact: number
  }[]
  recommendations: string[]
}

export interface RunbookStep {
  stepNumber: number
  urgency: 'IMMEDIATE' | 'SHORT_TERM' | 'RECOVERY'
  action: string
  detail: string
  targetSystem: string | null
  performedBy: 'automated' | 'manual'
  automatingAgent: string | null
  uipathProcess: string | null
  expectedEffect: string
  timeWindowMinutes: number
  validatedInSimulation: boolean
}

export interface Runbook {
  runbookId: string
  title: string
  generatedAt: number
  validated: boolean
  scenarioId: string
  triggerConditions: { metric: string; threshold: string; observedValue: number; severity: string }[]
  immediateActions: RunbookStep[]
  shortTermActions: RunbookStep[]
  recoveryActions: RunbookStep[]
  escalationChain: {
    level: number
    triggerCondition: string
    action: string
    uipathProcess: string
    automatedBy: string
    outcome: string
  }[]
  recoveryMilestones: {
    milestone: string
    targetMinutes: number
    achievedTick: number | null
    status: 'achieved' | 'not_achieved'
  }[]
  estimatedRecoveryMinutes: number
  markdownContent: string
}

export interface AgentCalibration {
  agentId: string
  agentName: string
  role: string
  currentLevel: number
  recommendedLevel: number
  trustScore: number
  totalActions: number
  effectiveActions: number
  counterproductiveActions: number
  accuracyPct: number
  stabilityContribution: number
  rationale: string
  readyForUpgrade: boolean
  requiresDowngrade: boolean
}

export interface CalibrationCertificate {
  certificateId: string
  generatedAt: number
  scenarioId: string
  overallAssessment: 'READY_FOR_EXPANDED_AUTOMATION' | 'ADEQUATE_WITH_MONITORING' | 'REQUIRES_HUMAN_OVERSIGHT'
  assessmentLabel: string
  assessmentColor: 'success' | 'warning' | 'danger'
  averageAccuracyPct: number
  averageTrustScore: number
  overallRecommendation: string
  agentsReadyForUpgrade: string[]
  agentsRequiringDowngrade: string[]
  agentCalibrations: AgentCalibration[]
  evidenceTrail: string[]
  scenarioOutcome: 'recovered' | 'degraded'
  crisisTicks: number
  note: string
}

export interface ProcessTemplate {
  processName: string
  xaml: string
  projectJson: object
  readme: string
  downloadFilename: string
  description: string
  inputArgs: { name: string; type: string; description: string }[]
  outputArgs: { name: string; type: string; description: string }[]
}
