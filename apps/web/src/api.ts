import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('current_user')
      window.dispatchEvent(new Event('forgesight:logout'))
    }
    return Promise.reject(error)
  },
)

export interface AuthUser {
  id: string
  email: string
  displayName?: string
  role?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export interface Inspection {
  id: string
  component_type: string
  part_identifier?: string
  batch_identifier?: string
  status?: string
  notes?: string
  created_at: string
}

export interface MediaFile {
  id: string
  inspection_id: string
  storage_key: string
  original_filename?: string
  content_type?: string
  file_size?: number
  width?: number
  height?: number
  sha256?: string
  created_at: string
}

export interface InferenceJob {
  id: string
  inspection_id: string
  status: string
  queued_at: string
  started_at?: string
  completed_at?: string
}

export interface InferenceResult {
  id: string
  job_id: string
  media_file_id: string
  predicted_label?: string | null
  confidence?: number | null
  overlay_url?: string
  segmentation_url?: string
  latency_ms?: number | null
}

export interface ModelVersion {
  name: string
  version: string
  stage: string
  status: string
  creation_timestamp?: number
}

export interface ModelInfo {
  name: string
  latest_version: string
  stages: Record<string, string>
  versions: ModelVersion[]
}

export const authAPI = {
  register: async (data: { email: string; password: string; display_name?: string; role?: string }) =>
    api.post<{ user: AuthUser }>('/auth/register', data).then(r => r.data),
  login: async (data: { email: string; password: string }) =>
    api.post<AuthResponse>('/auth/login', data).then(r => r.data),
  me: async () => api.get<AuthUser>('/auth/me').then(r => r.data),
}

export const inspectionAPI = {
  list: async () => api.get<Inspection[]>('/inspections').then(r => r.data),
  create: async (data: { component_type: string; part_identifier: string; notes?: string }) =>
    api.post<Inspection>('/inspections', data).then(r => r.data),
  get: async (id: string) => api.get<Inspection>(`/inspections/${id}`).then(r => r.data),
}

export const mediaAPI = {
  upload: async (inspectionId: string, file: File) => {
    const formData = new FormData()
    formData.append('files', file)
    return api.post<MediaFile[]>(`/inspections/${inspectionId}/media`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data[0])
  },
}

export const inferenceAPI = {
  createJob: async (inspectionId: string, modelVersionId?: string) =>
    api.post<InferenceJob>('/inference/jobs', { inspection_id: inspectionId, model_version_id: modelVersionId }).then(r => r.data),
  getJob: async (jobId: string) => api.get<InferenceJob>(`/inference/jobs/${jobId}`).then(r => r.data),
  getLatestJob: async (inspectionId: string) =>
    api.get<InferenceJob>(`/inference/inspections/${inspectionId}/jobs/latest`).then(r => r.data),
  getResult: async (jobId: string) => api.get<InferenceResult>(`/inference/results/${jobId}`).then(r => r.data),
}

export const modelAPI = {
  listRegistry: async () => api.get<ModelInfo[]>('/models/registry').then(r => r.data),
  transitionStage: async (modelName: string, version: string, stage: string, archiveExisting: boolean = true) =>
    api.post('/models/transition-stage', {
      model_name: modelName,
      version,
      stage,
      archive_existing: archiveExisting,
    }).then(r => r.data),
}

export default api
