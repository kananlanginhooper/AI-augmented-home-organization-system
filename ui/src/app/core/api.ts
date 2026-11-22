import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type { components } from './schema';

type S = components['schemas'];
export type UiConfig = S['RuntimeConfig'];
export type Overview = S['Overview'];
export type Progress = S['Progress'];
export type Space = S['SpaceSummary'];
export type SpaceIn = S['SpaceIn'];
export type Photo = S['PhotoOut'];
export type Item = S['ItemOut'];
export type ItemPatch = S['ItemPatch'];
export type Plan = S['PlanOut'];
export type PlanDetail = S['PlanDetail'];
export type PlanIn = S['PlanIn'];
export type Task = S['TaskOut'];
export type TaskPatch = S['TaskPatch'];
export type Checkin = S['CheckinOut'];
export type Job = S['JobOut'];
export type Evaluation = S['EvaluationOut'];
export type SendResult = S['SendResult'];
export type Phase = 'before' | 'progress' | 'after' | 'reference';

export const DISPOSITIONS = ['undecided', 'keep', 'donate', 'sell', 'trash', 'relocate'] as const;

/** Every call the UI makes. Paths are relative to <base href>, so the app works under any UI_BASE_PATH.
 *  The Pages demo swaps in a subclass with browser-only data (core/demo-api.ts). */
@Injectable({ providedIn: 'root' })
export class Api {
  protected readonly http = inject(HttpClient);
  readonly demo: boolean = false;

  protected get<T>(path: string, params: Record<string, string | number | boolean | undefined> = {}) {
    const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== '')) as Record<
      string,
      string | number | boolean
    >;
    return firstValueFrom(this.http.get<T>(`api/${path}`, { params: clean }));
  }
  protected send<T>(method: 'POST' | 'PATCH' | 'PUT' | 'DELETE', path: string, body?: unknown) {
    return firstValueFrom(this.http.request<T>(method, `api/${path}`, { body }));
  }

  config() {
    return this.get<UiConfig>('config');
  }
  overview() {
    return this.get<Overview>('overview');
  }

  spaces() {
    return this.get<Space[]>('spaces');
  }
  createSpace(body: SpaceIn) {
    return this.send<Space>('POST', 'spaces', body);
  }
  patchSpace(id: number, body: Partial<SpaceIn>) {
    return this.send<Space>('PATCH', `spaces/${id}`, body);
  }
  deleteSpace(id: number) {
    return this.send<void>('DELETE', `spaces/${id}`);
  }
  plans(spaceId: number) {
    return this.get<Plan[]>(`spaces/${spaceId}/plans`);
  }
  createPlan(spaceId: number, body: PlanIn) {
    return this.send<Plan>('POST', `spaces/${spaceId}/plans`, body);
  }
  review(spaceId: number) {
    return this.send<Job>('POST', `spaces/${spaceId}/review`);
  }
  checkins(spaceId: number) {
    return this.get<Checkin[]>(`spaces/${spaceId}/checkins`);
  }

  photos(spaceId?: number, unassigned = false) {
    return this.get<Photo[]>('photos', { space_id: spaceId, unassigned: unassigned || undefined });
  }
  upload(file: File, fields: { spaceId?: number; phase: Phase; caption?: string }) {
    const form = new FormData();
    form.append('file', file);
    form.append('phase', fields.phase);
    if (fields.spaceId != null) form.append('space_id', String(fields.spaceId));
    if (fields.caption) form.append('caption', fields.caption);
    return firstValueFrom(this.http.post<S['UploadResult']>('api/photos', form));
  }
  photoUrl(photo: Pick<Photo, 'id'>, size: 'full' | 'thumb' | 'claude' = 'thumb') {
    return `api/photos/${photo.id}/file?size=${size}`;
  }
  patchPhoto(id: number, body: S['PhotoPatch']) {
    return this.send<Photo>('PATCH', `photos/${id}`, body);
  }
  deletePhoto(id: number) {
    return this.send<void>('DELETE', `photos/${id}`);
  }
  analyze(id: number) {
    return this.send<Job>('POST', `photos/${id}/analyze`);
  }
  evaluations(id: number) {
    return this.get<Evaluation[]>(`photos/${id}/evaluations`);
  }

  items(filter: { spaceId?: number; q?: string; disposition?: string; unconfirmed?: boolean } = {}) {
    return this.get<Item[]>('items', {
      space_id: filter.spaceId,
      q: filter.q,
      disposition: filter.disposition,
      unconfirmed: filter.unconfirmed || undefined,
    });
  }
  createItem(body: S['ItemIn']) {
    return this.send<Item>('POST', 'items', body);
  }
  patchItem(id: number, body: ItemPatch) {
    return this.send<Item>('PATCH', `items/${id}`, body);
  }
  deleteItem(id: number) {
    return this.send<void>('DELETE', `items/${id}`);
  }

  plan(id: number) {
    return this.get<PlanDetail>(`plans/${id}`);
  }
  setPlanStatus(id: number, status: 'active' | 'done' | 'archived') {
    return firstValueFrom(this.http.post<Plan>(`api/plans/${id}/status`, null, { params: { status } }));
  }
  addTask(planId: number, body: S['TaskIn']) {
    return this.send<Task>('POST', `plans/${planId}/tasks`, body);
  }
  patchTask(id: number, body: TaskPatch) {
    return this.send<Task>('PATCH', `tasks/${id}`, body);
  }
  deleteTask(id: number) {
    return this.send<void>('DELETE', `tasks/${id}`);
  }
  sendToGamePlan(body: S['SendToGamePlanIn']) {
    return this.send<SendResult>('POST', 'gameplan/send', body);
  }
  syncGamePlan() {
    return this.send<{ marked_done: number; marked_skipped: number }>('POST', 'gameplan/sync');
  }

  jobs(status?: string) {
    return this.get<Job[]>('ai/jobs', { status });
  }
  retryJob(id: number) {
    return this.send<Job>('POST', `ai/jobs/${id}/retry`);
  }
}
