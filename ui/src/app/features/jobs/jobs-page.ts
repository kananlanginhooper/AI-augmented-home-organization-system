import { ChangeDetectionStrategy, Component, inject, resource } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { Api, type Job } from '../../core/api';
import { ConfigService } from '../../core/config.service';
import { ago, JOB_TONE } from '../../shared/format';
import { StatusPill } from '../../shared/for-apps/status';
import { StackTable } from '../../shared/for-apps/stack-table';

/** The Claude work queue: what's waiting, who ran what, and what failed. */
@Component({
  selector: 'app-jobs-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StatusPill, StackTable, MatButtonModule, MatTableModule],
  template: `
    <div class="how">
      @if (cfg()?.claude?.apiWorker) {
        The API runs these jobs itself with <b>{{ cfg()?.claude?.model }}</b>. A Claude Code thread can still take one.
      } @else {
        No Claude API key is set, so jobs wait here for a Claude Code thread. In a session:
        <code>python tools/thread_jobs.py claim</code>, look at the photos it saves, write the answer and
        <code>python tools/thread_jobs.py submit &lt;id&gt; answer.json</code>.
      }
      <button mat-button (click)="jobs.reload()">Refresh</button>
    </div>
    <table mat-table appStackTable [dataSource]="jobs.value() ?? []">
      <ng-container matColumnDef="id"><th mat-header-cell *matHeaderCellDef>#</th><td mat-cell *matCellDef="let j">{{ j.id }}</td></ng-container>
      <ng-container matColumnDef="kind">
        <th mat-header-cell *matHeaderCellDef>Job</th>
        <td mat-cell *matCellDef="let j">{{ label[j.kind] ?? j.kind }} <span class="meta">#{{ j.target_id }}</span></td>
      </ng-container>
      <ng-container matColumnDef="status">
        <th mat-header-cell *matHeaderCellDef>Status</th>
        <td mat-cell *matCellDef="let j">
          <app-pill [tone]="tone[j.status]">{{ j.status }}</app-pill>
          @if (j.worker) { <span class="meta">{{ j.worker }}</span> }
          @if (j.error) { <div class="error">{{ j.error }}</div> }
        </td>
      </ng-container>
      <ng-container matColumnDef="when">
        <th mat-header-cell *matHeaderCellDef>When</th>
        <td mat-cell *matCellDef="let j">{{ ago(j.finished_at ?? j.created_at) }}</td>
      </ng-container>
      <ng-container matColumnDef="actions">
        <th mat-header-cell *matHeaderCellDef></th>
        <td mat-cell *matCellDef="let j">
          @if ((j.status === 'failed' || j.status === 'running') && !api.demo) {
            <button mat-button (click)="retry(j)">{{ j.status === 'running' ? 'Release' : 'Retry' }}</button>
          }
        </td>
      </ng-container>
      <tr mat-header-row *matHeaderRowDef="columns"></tr>
      <tr mat-row *matRowDef="let row; columns: columns"></tr>
      <tr class="mat-row" *matNoDataRow><td class="app-empty" [attr.colspan]="columns.length">No jobs yet.</td></tr>
    </table>
  `,
  styles: `
    .how { font: var(--app-text-sm); color: var(--app-muted); margin-bottom: var(--app-space-4); }
    code { font-family: var(--app-font-mono); background: var(--app-card); padding: 0 4px; border-radius: 4px; }
    table { width: 100%; background: var(--app-card); }
    .meta { font: var(--app-text-xs); color: var(--app-muted); }
    .error { font: var(--app-text-xs); color: var(--app-bad); max-width: 520px; }
  `,
})
export class JobsPage {
  readonly api = inject(Api);
  readonly cfg = inject(ConfigService).config;
  readonly jobs = resource({ loader: () => this.api.jobs() });
  readonly columns = ['id', 'kind', 'status', 'when', 'actions'];
  readonly tone = JOB_TONE;
  readonly ago = ago;
  readonly label: Partial<Record<string, string>> = {
    analyze_photo: 'Look at a photo',
    make_plan: 'Write a plan',
    review_progress: 'Review progress',
  };

  async retry(j: Job) {
    await this.api.retryJob(j.id);
    this.jobs.reload();
  }
}
