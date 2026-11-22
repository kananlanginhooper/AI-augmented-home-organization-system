import { formatDistanceToNowStrict, parseISO } from 'date-fns';

/** API datetimes are naive UTC ("2026-11-22T18:04:00"); treat them as UTC. */
export function ago(iso: string | null | undefined): string {
  if (!iso) return '';
  return formatDistanceToNowStrict(parseISO(iso.endsWith('Z') ? iso : iso + 'Z'), { addSuffix: true });
}

export function minutes(total: number): string {
  if (total < 60) return `${total} min`;
  const h = Math.floor(total / 60);
  const m = total % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}

export function percent(part: number, whole: number): number {
  return whole ? Math.round((part / whole) * 100) : 0;
}

export function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export const DISPOSITION_TONE: Record<string, string | null> = {
  keep: 'ok',
  donate: 'warn',
  sell: 'warn',
  trash: 'bad',
  relocate: null,
  undecided: null,
};

export const JOB_TONE: Record<string, string | null> = { done: 'ok', running: 'warn', pending: null, failed: 'bad' };
