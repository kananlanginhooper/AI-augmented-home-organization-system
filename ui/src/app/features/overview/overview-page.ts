import { ChangeDetectionStrategy, Component, computed, inject, resource } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { Api, type Task } from '../../core/api';
import { ago, minutes, percent } from '../../shared/format';
import { ProgressLine } from '../../shared/progress-line';
import { TaskRow } from '../../shared/task-row';
import { StatTile, EmptyState } from '../../shared/for-apps/status';

@Component({
  selector: 'app-overview-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StatTile, EmptyState, RouterLink, MatButtonModule, ProgressLine, TaskRow],
  templateUrl: './overview-page.html',
  styleUrl: './overview-page.scss',
})
export class OverviewPage {
  private readonly api = inject(Api);
  readonly data = resource({ loader: () => this.api.overview() });
  readonly ago = ago;

  readonly tiles = computed(() => {
    const o = this.data.value();
    if (!o) return [];
    const p = o.progress;
    return [
      { label: 'Steps done', value: `${p.tasks_done}/${p.tasks_total}`, hint: `${percent(p.tasks_done, p.tasks_total)}%` },
      { label: 'Time done', value: minutes(p.minutes_done), hint: `of ${minutes(p.minutes_total)} planned` },
      { label: 'Items decided', value: `${p.items_decided}/${p.items_total}`, hint: `${o.open_decisions} to review` },
      { label: 'Photos', value: String(p.photos), hint: `${o.pending_jobs} Claude job(s) waiting` },
    ];
  });

  /** Rooms only on the overview; zones and containers show on their room's page. */
  readonly rooms = computed(() => (this.data.value()?.spaces ?? []).filter((s) => s.parent_id == null));

  spaceName(id: number | null | undefined): string {
    return this.data.value()?.spaces.find((s) => s.id === id)?.path ?? '';
  }

  async setStatus(t: Task, status: 'todo' | 'doing' | 'done' | 'skipped') {
    await this.api.patchTask(t.id, { status });
    this.data.reload();
  }

  async remove(t: Task) {
    await this.api.deleteTask(t.id);
    this.data.reload();
  }
}
