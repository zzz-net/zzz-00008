export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

export function isOverdue(deadline: string): boolean {
  return new Date(deadline) < new Date();
}

export function getEntityLabel(entityType: string, entityId: number): string {
  if (entityType === 'ticket') return `升级单 #${entityId}`;
  if (entityType === 'batch') return `交接批次 #${entityId}`;
  if (entityType === 'shift') return `排班班次 #${entityId}`;
  return `${entityType} #${entityId}`;
}
