import React, { useEffect, useState } from 'react'
import { Inspection, InferenceJob, inspectionAPI, inferenceAPI } from '../api'

interface InspectionWithJob extends Inspection {
  latestJob?: InferenceJob
}

interface Props {
  onViewResult: (jobId: string, inspectionId: string) => void
  refreshTrigger: number
}

export default function InspectionList({ onViewResult, refreshTrigger }: Props) {
  const [inspections, setInspections] = useState<InspectionWithJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadInspections = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await inspectionAPI.list()
        const inspectionsWithJobs = await Promise.all(
          data.map(async (inspection) => {
            try {
              const latestJob = await inferenceAPI.getLatestJob(inspection.id)
              return { ...inspection, latestJob }
            } catch {
              return inspection
            }
          }),
        )
        setInspections(inspectionsWithJobs)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load inspections')
      } finally {
        setLoading(false)
      }
    }

    loadInspections()
  }, [refreshTrigger])

  if (loading) {
    return <div className="container"><p className="loading">Loading inspections...</p></div>
  }

  if (error) {
    return <div className="container"><p className="error">Error: {error}</p></div>
  }

  if (inspections.length === 0) {
    return (
      <div className="container">
        <div className="empty-state">
          <h2>No inspections yet</h2>
          <p>Create a new inspection to get started</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <h2>Inspections</h2>
      <div className="inspection-grid">
        {inspections.map((inspection) => (
          <div key={inspection.id} className="inspection-card">
            <div className="card-header">
              <h3>{inspection.component_type}</h3>
              <span className="part-id">{inspection.part_identifier}</span>
            </div>
            <div className="card-body">
              <p>
                <strong>ID:</strong> <code>{inspection.id.slice(0, 8)}</code>
              </p>
              <p>
                <strong>Created:</strong> {new Date(inspection.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="card-actions">
              <button
                className="btn btn-primary"
                disabled={!inspection.latestJob}
                onClick={() => {
                  if (inspection.latestJob) {
                    onViewResult(inspection.latestJob.id, inspection.id)
                  }
                }}
              >
                {inspection.latestJob ? 'View Result' : 'No Result'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
