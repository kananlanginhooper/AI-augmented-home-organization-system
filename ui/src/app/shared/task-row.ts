import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import type { Task } from '../core/api';

/** One checklist step: check it off, see its first step and supplies, skip or delete it. */
@Component({
  selector: 'app-task-row',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatCheckboxModule, MatIconModule, MatButtonModule, MatMenuModule],
  template: `
    <mat-checkbox
      [checked]="t().status === 'done'"
      [disabled]="blocked() && t().status !== 'done'"
      (change)="status.emit($event.checked ? 'done' : 'todo')"
      [aria-label]="'Done: ' + t().title"
    />
    <div class="body" [class.done]="t().status === 'done'" [class.skipped]="t().status === 'skipped'">
      <div class="title">
        {{ t().title }}
        <span class="app-pill">{{ t().phase }}</span>
        <span class="meta">{{ t().est_minutes }} min</span>
        @if (t().priority === 1) {
          <span class="app-pill" data-tone="warn">first</span>
        }
        @if (t().gameplan_task_id) {
          <span class="app-pill" data-tone="ok">Game Plan {{ t().gameplan_date }}</span>
        }
        @if (blocked() && t().status !== 'done') {
          <span class="meta">waits on an earlier step</span>
        }
      </div>
      @if (showDetail()) {
        @if (t().first_step) {
          <div class="first"><b>Start:</b> {{ t().first_step }}</div>
        }
        @if (t().detail) {
          <div class="detail">{{ t().detail }}</div>
        }
        @if (t().supplies?.length) {
          <div class="detail"><b>Supplies:</b> {{ t().supplies!.join(', ') }}</div>
        }
      }
    </div>
    <button mat-icon-button [matMenuTriggerFor]="menu" aria-label="Step actions"><mat-icon>more_vert</mat-icon></button>
    <mat-menu #menu="matMenu">
      @if (t().status !== 'doing') {
        <button mat-menu-item (click)="status.emit('doing')">Mark in progress</button>
      }
      @if (t().status !== 'skipped') {
        <button mat-menu-item (click)="status.emit('skipped')">Skip</button>
      } @else {
        <button mat-menu-item (click)="status.emit('todo')">Un-skip</button>
      }
      <button mat-menu-item (click)="remove.emit()">Delete</button>
    </mat-menu>
  `,
  styles: `
    :host { display: grid; grid-template-columns: auto 1fr auto; align-items: start; gap: var(--app-space-2);
      padding: var(--app-space-2) 0; border-bottom: 1px solid var(--app-line); }
    .body { min-width: 0; padding-top: 10px; }
    .title { display: flex; flex-wrap: wrap; align-items: center; gap: var(--app-space-2); font: var(--app-text-md); }
    .meta { font: var(--app-text-xs); color: var(--app-muted); }
    .first, .detail { font: var(--app-text-sm); color: var(--app-muted); margin-top: 2px; }
    .first b, .detail b { color: var(--app-ink); font-weight: 600; }
    .done .title { text-decoration: line-through; color: var(--app-muted); }
    .skipped { opacity: 0.55; }
  `,
})
export class TaskRow {
  readonly t = input.required<Task>();
  readonly blocked = input(false);
  readonly showDetail = input(true);
  readonly status = output<'todo' | 'doing' | 'done' | 'skipped'>();
  readonly remove = output<void>();
}
