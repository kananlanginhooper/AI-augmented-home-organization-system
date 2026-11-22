import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Api, type Task } from '../../core/api';
import { minutes, today } from '../../shared/format';

/** Pick open steps and put them on Game Plan's calendar, filling each day up to a time budget. */
@Component({
  selector: 'app-send-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, MatButtonModule, MatCheckboxModule, MatDialogModule, MatFormFieldModule, MatInputModule],
  template: `
    <h2 mat-dialog-title>Send steps to Game Plan</h2>
    <mat-dialog-content>
      <div class="row">
        <mat-form-field subscriptSizing="dynamic">
          <mat-label>Start on</mat-label>
          <input matInput type="date" [(ngModel)]="date" />
        </mat-form-field>
        <mat-form-field subscriptSizing="dynamic">
          <mat-label>Minutes per day</mat-label>
          <input matInput type="number" min="10" [(ngModel)]="perDay" />
        </mat-form-field>
      </div>
      @for (t of data.tasks; track t.id) {
        <mat-checkbox [checked]="picked().has(t.id)" (change)="toggle(t.id)">
          {{ t.title }} <span class="meta">{{ t.est_minutes }} min</span>
        </mat-checkbox>
      }
      <p class="meta">{{ picked().size }} steps, {{ total() }}. They go to Game Plan's "{{ data.area }}" area, in checklist order.</p>
      @if (error()) {
        <p class="error">{{ error() }}</p>
      }
    </mat-dialog-content>
    <mat-dialog-actions>
      <button mat-button mat-dialog-close>Cancel</button>
      <button mat-flat-button [disabled]="!picked().size || busy()" (click)="send()">Send {{ picked().size }}</button>
    </mat-dialog-actions>
  `,
  styles: `
    .row { display: flex; flex-wrap: wrap; gap: var(--app-space-3); margin-bottom: var(--app-space-3); }
    mat-checkbox { display: block; }
    .meta { font: var(--app-text-xs); color: var(--app-muted); }
    .error { color: var(--app-bad); font: var(--app-text-sm); white-space: pre-line; }
  `,
})
export class SendDialog {
  private readonly api = inject(Api);
  private readonly ref = inject(MatDialogRef<SendDialog>);
  readonly data = inject<{ tasks: Task[]; area: string }>(MAT_DIALOG_DATA);
  readonly picked = signal(new Set(this.data.tasks.map((t) => t.id)));
  readonly total = computed(() => minutes(this.data.tasks.filter((t) => this.picked().has(t.id)).reduce((n, t) => n + t.est_minutes, 0)));
  readonly busy = signal(false);
  readonly error = signal('');
  date = today();
  perDay = 60;

  toggle(id: number) {
    const next = new Set(this.picked());
    if (next.has(id)) next.delete(id);
    else next.add(id);
    this.picked.set(next);
  }

  async send() {
    this.busy.set(true);
    try {
      const r = await this.api.sendToGamePlan({ task_ids: [...this.picked()], date: this.date, per_day_minutes: this.perDay });
      if (r.errors.length) this.error.set(`Sent ${r.sent.length}. Problems:\n` + r.errors.join('\n'));
      else this.ref.close(true);
    } catch (e) {
      this.error.set((e as { error?: { detail?: string } }).error?.detail ?? 'Game Plan didn’t answer.');
    } finally {
      this.busy.set(false);
    }
  }
}
