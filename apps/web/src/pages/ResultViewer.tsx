import React, { useEffect, useState } from 'react'
import { InferenceJob, InferenceResult, inferenceAPI } from '../api'

interface Props {
  jobId: string
  inspectionId: string
}

export default function ResultViewer({ jobId, inspectionId }: Props) {
  const [job, setJob] = useState<InferenceJob | null>(null)
  const [result, setResult] = useState<InferenceResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadResult = async () => {
      try {
        setLoading(true)
        setError(null)

        // Get job status
        const jobData = await inferenceAPI.getJob(jobId)
        setJob(jobData)

        // If job is completed, fetch result
        if (jobData.status === 'completed') {
          try {
            const resultData = await inferenceAPI.getResult(jobId)
            setResult(resultData)
          } catch (err) {
            // Result not yet available
            console.log('Result not yet available')
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load result')
      } finally {
        setLoading(false)
      }
    }

    const interval = setInterval(loadResult, 2000)
    loadResult()
    return () => clearInterval(interval)
  }, [jobId])

  if (loading) {
    return <div className="container"><p className="loading">Loading result...</p></div>
  }

  if (error) {
    return <div className="container"><p className="error">Error: {error}</p></div>
  }

  if (!job) {
    return <div className="container"><p>Job not found</p></div>
  }

  const isProcessing = job.status !== 'completed'
  const overlayUrl = result?.overlay_url
  const segmentationUrl = result?.segmentation_url
  const predictedLabel = result?.predicted_label || 'unknown'

  return (
    <div className="container">
      <h2>Inspection Result</h2>

      <div className="result-container">
        <div className="result-header">
          <div className="result-info">
            <p>
              <strong>Job ID:</strong> <code>{jobId.slice(0, 12)}</code>
            </p>
            <p>
              <strong>Status:</strong>{' '}
              <span className={`status status-${job.status}`}>{job.status.toUpperCase()}</span>
            </p>
            {result && (
              <>
                <p>
                  <strong>Prediction:</strong>{' '}
                  <span className={`label label-${predictedLabel}`}>
                    {predictedLabel.toUpperCase()}
                  </span>
                </p>
                <p>
                  <strong>Confidence:</strong> {result.confidence ?? 0}%
                </p>
                <p>
                  <strong>Latency:</strong> {result.latency_ms ?? 0}ms
                </p>
              </>
            )}
          </div>

          {isProcessing && (
            <div className="processing-indicator">
              <div className="spinner"></div>
              <p>Processing...</p>
            </div>
          )}
        </div>

        {overlayUrl && (
          <div className="result-images">
            <div className="image-section">
              <h3>Detection Overlay</h3>
              <img src={overlayUrl} alt="Detection overlay" className="result-image" />
            </div>
            {segmentationUrl && (
              <div className="image-section">
                <h3>Segmentation Mask</h3>
                <img src={segmentationUrl} alt="Segmentation mask" className="result-image" />
              </div>
            )}
          </div>
        )}

        {!overlayUrl && result && (
          <div className="no-images">
            <p>No image overlays available</p>
          </div>
        )}
      </div>
    </div>
  )
}
