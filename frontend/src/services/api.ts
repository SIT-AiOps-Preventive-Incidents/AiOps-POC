import { http } from "./http";
import type {
  AppRecord,
  Deployment,
  DiscoveryResponse,
  HostDetailResponse,
  HostRecord,
  Incident,
  NotificationRecord,
  OverviewResponse,
  RunbookRecord,
  ServiceDetailResponse,
  ServiceMapResponse,
  SettingsResponse,
  SkillRecord,
  TraceSpan,
  VerifyResponse,
} from "@/types/api";

export interface AppInput {
  name?: string;
  service_name: string;
  language?: string;
  team?: string;
  owner?: string;
  repo?: string;
  environment?: string;
  container?: string;
  admin_url?: string;
}
export interface HostInput {
  name: string;
  address: string;
  os?: string;
  environment?: string;
  labels?: Record<string, string>;
}
export interface HostRegistration {
  name: string;
  os?: string;
  arch?: string;
  kind?: "server" | "workstation";
}

export const api = {
  overview: () => http.get<OverviewResponse>("/api/overview"),
  serviceMap: () => http.get<ServiceMapResponse>("/api/servicemap"),
  topology: () =>
    http.get<Array<{ from: string; to: string; count: number }>>(
      "/api/topology",
    ),
  apps: () => http.get<AppRecord[]>("/api/apps"),
  createApp: (body: AppInput) => http.post<AppRecord>("/api/apps", body),
  deleteApp: (id: number) => http.delete<{ ok: boolean }>(`/api/apps/${id}`),
  service: (name: string) =>
    http.get<ServiceDetailResponse>(
      `/api/services/${encodeURIComponent(name)}`,
    ),
  verifyApp: (name: string) =>
    http.get<VerifyResponse>(`/api/apps/${encodeURIComponent(name)}/verify`),
  discover: () => http.get<DiscoveryResponse>("/api/discover"),
  traces: (id: string) =>
    http.get<TraceSpan[]>(`/api/traces/${encodeURIComponent(id)}`),
  hosts: () => http.get<HostRecord[]>("/api/hosts"),
  createHost: (body: HostInput) => http.post<HostRecord>("/api/hosts", body),
  registerHost: (body: HostRegistration) =>
    http.post<HostRecord>("/api/hosts/register", body),
  host: (name: string) =>
    http.get<HostDetailResponse>(`/api/hosts/${encodeURIComponent(name)}`),
  deleteHost: (id: number) => http.delete<{ ok: boolean }>(`/api/hosts/${id}`),
  incidents: () => http.get<Incident[]>("/api/incidents"),
  incident: (id: number) => http.get<Incident>(`/api/incidents/${id}`),
  approveIncident: (
    id: number,
    body: {
      approver: string;
      action_index: number;
      comment: string;
      owner_confirmed: boolean;
    },
  ) => http.post<Incident>(`/api/incidents/${id}/approve`, body),
  rejectIncident: (id: number, body: { approver: string; comment: string }) =>
    http.post<{ ok: boolean }>(`/api/incidents/${id}/reject`, body),
  closeIncident: (id: number) =>
    http.post<{ ok: boolean }>(`/api/incidents/${id}/close`),
  reanalyzeIncident: (id: number) =>
    http.post<{ ok: boolean }>(`/api/incidents/${id}/reanalyze`),
  feedback: (
    id: number,
    body: { score: number; rca_correct: boolean; comment: string },
  ) =>
    http.post<{ ok: boolean; message: string }>(
      `/api/incidents/${id}/feedback`,
      body,
    ),
  deployments: () => http.get<Deployment[]>("/api/deployments"),
  createDeployment: (body: {
    service: string;
    version: string;
    commit: string;
    author?: string;
    message?: string;
    profile?: string;
  }) => http.post<{ id: number; warning?: string }>("/api/deployments", body),
  skills: () => http.get<SkillRecord[]>("/api/skills"),
  runbooks: () => http.get<RunbookRecord[]>("/api/runbooks"),
  toggleRunbook: (id: number) =>
    http.post<{ ok: boolean }>(`/api/runbooks/${id}/toggle`),
  notifications: () => http.get<NotificationRecord[]>("/api/notifications"),
  settings: () => http.get<SettingsResponse>("/api/settings"),
  saveSettings: (body: Record<string, string>) =>
    http.put<Record<string, string>>("/api/settings", body),
  testTeams: () => http.post<{ status: string }>("/api/settings/test-teams"),
  chaos: (scenario: string) =>
    http.post<Record<string, unknown>>(
      `/api/chaos/${encodeURIComponent(scenario)}`,
    ),
};
