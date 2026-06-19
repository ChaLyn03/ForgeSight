import React, { useState } from 'react'
import { inspectionAPI, mediaAPI, inferenceAPI } from '../api'

interface Props {
  onSuccess: () => void
}

export default function InspectionUpload({ onSuccess }: Props) {
  const [componentType, setComponentType] = useState('sensor')
  const [partId, setPartId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !partId) {
      setError('Please fill in all fields')
      return
    }

    try {
      setLoading(true)
      setError(null)
      setSuccessMessage(null)

      // 1. Create inspection
      const inspection = await inspectionAPI.create({
        component_type: componentType,
        part_identifier: partId,
      })

      // 2. Upload media
      await mediaAPI.upload(inspection.id, file)

      // 3. Create inference job
      const job = await inferenceAPI.createJob(inspection.id)

      setSuccessMessage(`Inspection submitted! Job ID: ${job.id.slice(0, 8)}`)
      setComponentType('sensor')
      setPartId('')
      setFile(null)

      // Reset form and navigate
      setTimeout(() => {
        onSuccess()
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit inspection')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="form-container">
        <h2>New Inspection</h2>

        {error && <div className="alert alert-error">{error}</div>}
        {successMessage && <div className="alert alert-success">{successMessage}</div>}

        <form onSubmit={handleSubmit} className="inspection-form">
          <div className="form-group">
            <label htmlFor="componentType">Component Type</label>
            <select
              id="componentType"
              value={componentType}
              onChange={(e) => setComponentType(e.target.value)}
              disabled={loading}
            >
              <option value="sensor">Sensor</option>
              <option value="pcb">PCB Board</option>
              <option value="connector">Connector</option>
              <option value="housing">Housing</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="partId">Part Identifier</label>
            <input
              id="partId"
              type="text"
              placeholder="e.g., SENS-001"
              value={partId}
              onChange={(e) => setPartId(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="file">Image File</label>
            <input
              id="file"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              disabled={loading}
              required
            />
            {file && <p className="file-selected">{file.name}</p>}
          </div>

          <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
            {loading ? 'Submitting...' : 'Submit Inspection'}
          </button>
        </form>
      </div>
    </div>
  )
}
