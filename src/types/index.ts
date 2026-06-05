export type Severity = 'low' | 'medium' | 'high' | 'critical';
export type TicketStatus = 'open' | 'in_progress' | 'closed' | 'overdue';
export type BatchStatus = 'pending' | 'confirmed' | 'returned';
export type Role = 'cs' | 'handover' | 'receiver';
export type EntityType = 'ticket' | 'batch' | 'shift' | 'reminder' | 'plan';

export interface DutyShift {
  id: number;
  name: string;
  duty_person: string;
  start_time: string;
  end_time: string;
  allowed_severities: Severity[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface Ticket {
  id: number;
  customer_name: string;
  severity: Severity;
  assignee: string;
  deadline: string;
  progress: string;
  status: TicketStatus;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface HandoverBatch {
  id: number;
  name: string;
  description: string;
  status: BatchStatus;
  handover_person: string;
  receiver_person: string | null;
  original_confirmer: string | null;
  shift_id: number | null;
  shift_name: string | null;
  shift_duty_person: string | null;
  created_at: string;
  confirmed_at: string | null;
  revoked_at: string | null;
  revoked_by: string | null;
  revoke_reason: string | null;
  revoke_old_status: string | null;
  revoke_new_status: string | null;
  ticket_ids: number[];
  tickets?: Ticket[];
  affected_tickets?: Ticket[];
}

export interface StatusHistory {
  id: number;
  entity_type: EntityType;
  entity_id: number;
  old_status: string | null;
  new_status: string;
  operator: string;
  reason: string | null;
  created_at: string;
}

export interface RoleInfo {
  role: Role;
  name: string;
  permissions: string[];
}

export interface UserInfo {
  role: Role;
  username: string;
  name: string;
  permissions: string[];
}

export interface DashboardStats {
  tickets: {
    total: number;
    by_status: Record<TicketStatus, number>;
    by_severity: Record<Severity, number>;
  };
  batches: {
    total: number;
    pending: number;
    confirmed: number;
    returned: number;
  };
  recent_activity: StatusHistory[];
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface TicketListResponse {
  items: Ticket[];
  total: number;
  page: number;
  page_size: number;
}

export const severityMap: Record<Severity, { label: string; color: string }> = {
  low: { label: '低危', color: 'bg-green-100 text-green-800 border-green-300' },
  medium: { label: '中危', color: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  high: { label: '高危', color: 'bg-orange-100 text-orange-800 border-orange-300' },
  critical: { label: '严重', color: 'bg-red-100 text-red-800 border-red-300' },
};

export const statusMap: Record<TicketStatus, { label: string; color: string }> = {
  open: { label: '待处理', color: 'bg-blue-100 text-blue-800 border-blue-300' },
  in_progress: { label: '处理中', color: 'bg-purple-100 text-purple-800 border-purple-300' },
  closed: { label: '已关闭', color: 'bg-gray-100 text-gray-800 border-gray-300' },
  overdue: { label: '已逾期', color: 'bg-red-100 text-red-800 border-red-300' },
};

export const batchStatusMap: Record<BatchStatus, { label: string; color: string }> = {
  pending: { label: '待确认', color: 'bg-blue-100 text-blue-800 border-blue-300' },
  confirmed: { label: '已确认', color: 'bg-green-100 text-green-800 border-green-300' },
  returned: { label: '已退回', color: 'bg-red-100 text-red-800 border-red-300' },
};

export const roleMap: Record<Role, { label: string; color: string }> = {
  cs: { label: '普通客服', color: 'bg-slate-100 text-slate-800' },
  handover: { label: '交班人', color: 'bg-amber-100 text-amber-800' },
  receiver: { label: '接班人', color: 'bg-teal-100 text-teal-800' },
};

export interface ReminderConfirmation {
  id: number;
  reminder_id: number;
  confirmed_by: string;
  confirmed_at: string;
}

export interface DutyReminder {
  id: number;
  title: string;
  content: string;
  shift_id: number | null;
  shift_name: string | null;
  shift_duty_person: string | null;
  shift_date: string | null;
  effective_start: string;
  effective_end: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
  confirmations: ReminderConfirmation[];
}

export interface UpgradePlan {
  id: number;
  plan_group_id: string;
  title: string;
  applicable_severity: Severity;
  keywords: string[];
  steps: string;
  assignee_suggestion: string | null;
  is_active: boolean;
  version: number;
  is_latest: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
  match_score?: number;
  matched_keywords?: string[];
}

export interface PlanReferenceResult {
  plan: UpgradePlan;
  referenced_at: string;
  operator: string;
}
