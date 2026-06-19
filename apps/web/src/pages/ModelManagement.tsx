import React, { useEffect, useState } from 'react'
import { ModelInfo, modelAPI } from '../api'
import '../styles/ModelManagement.css'

export default function ModelManagement() {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null)
  const [transitioning, setTransitioning] = useState<string | null>(null)

  useEffect(() => {
    const loadModels = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await modelAPI.listRegistry()
        setModels(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load model registry')
      } finally {
        setLoading(false)
      }
    }

    loadModels()
  }, [])

  const handleTransition = async (modelName: string, version: string, stage: string) => {
    try {
      setTransitioning(`${modelName}-${version}`)
      await modelAPI.transitionStage(modelName, version, stage, true)
      // Refresh models
      const data = await modelAPI.listRegistry()
      setModels(data)
      setSelectedModel(data.find(m => m.name === modelName) || null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to transition model')
    } finally {
      setTransitioning(null)
    }
  }

  if (loading) {
    return <div className="container"><p className="loading">Loading model registry...</p></div>
  }

  if (error) {
    return <div className="container"><p className="error">Error: {error}</p></div>
  }

  if (models.length === 0) {
    return (
      <div className="container">
        <div className="empty-state">
          <h2>No Models Registered</h2>
          <p>Train a baseline model and register it in MLflow to see it here.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <h2>Model Registry</h2>

      <div className="model-registry">
        <div className="model-list">
          <h3>Registered Models</h3>
          {models.map((model) => (
            <div
              key={model.name}
              className={`model-card ${selectedModel?.name === model.name ? 'selected' : ''}`}
              onClick={() => setSelectedModel(model)}
            >
              <div className="model-name">{model.name}</div>
              <div className="model-meta">
                <span className="version-badge">v{model.latest_version}</span>
                {Object.keys(model.stages).length > 0 && (
                  <span className="stages-badge">{Object.keys(model.stages).length} stages</span>
                )}
              </div>
            </div>
          ))}
        </div>

        {selectedModel && (
          <div className="model-details">
            <div className="details-header">
              <h3>{selectedModel.name}</h3>
              <p className="details-path">Model: {selectedModel.name}</p>
            </div>

            <div className="stages-summary">
              <h4>Model Stages</h4>
              <div className="stages-grid">
                {['Production', 'Staging', 'Archived'].map((stage) => (
                  <div key={stage} className={`stage-box ${selectedModel.stages[stage] ? 'active' : ''}`}>
                    <div className="stage-name">{stage}</div>
                    {selectedModel.stages[stage] && (
                      <div className="stage-version">v{selectedModel.stages[stage]}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="versions-table">
              <h4>All Versions</h4>
              <table>
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Current Stage</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedModel.versions.map((version) => (
                    <tr key={version.version}>
                      <td className="monospace">v{version.version}</td>
                      <td>
                        <span className={`stage-badge stage-${version.stage.toLowerCase()}`}>
                          {version.stage}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge status-${version.status.toLowerCase()}`}>
                          {version.status}
                        </span>
                      </td>
                      <td className="date">
                        {version.creation_timestamp
                          ? new Date(version.creation_timestamp).toLocaleDateString()
                          : 'N/A'}
                      </td>
                      <td className="actions">
                        <div className="action-buttons">
                          {version.stage !== 'Production' && (
                            <button
                              className="btn-small btn-primary"
                              disabled={transitioning === `${selectedModel.name}-${version.version}`}
                              onClick={() => handleTransition(selectedModel.name, version.version, 'Production')}
                            >
                              {transitioning === `${selectedModel.name}-${version.version}` ? '...' : 'Promote'}
                            </button>
                          )}
                          {version.stage !== 'Archived' && (
                            <button
                              className="btn-small btn-secondary"
                              disabled={transitioning === `${selectedModel.name}-${version.version}`}
                              onClick={() => handleTransition(selectedModel.name, version.version, 'Archived')}
                            >
                              {transitioning === `${selectedModel.name}-${version.version}` ? '...' : 'Archive'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
