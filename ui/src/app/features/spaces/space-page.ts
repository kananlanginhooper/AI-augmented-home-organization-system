import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  numberAttribute,
  resource,
  signal,
  untracked,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { Router, RouterLink } from '@angular/router';
import { Api, type PlanIn, type Task } from '../../core/api';
import { ConfigService } from '../../core/config.service';
import { ago } from '../../shared/format';
import { ProgressLine } from '../../shared/progress-line';
import { TaskRow } from '../../shared/task-row';
import { PlanForm } from './plan-form';
import { SendDialog } from './send-dialog';

/** One space: its photos, its plan and checklist, decisions, shopping, Game Plan hand-off and check-ins. */
@Component({
  selector: 'app-space-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    RouterLink,
    PlanForm,
    ProgressLine,
    TaskRow,
  ],
  templateUrl: './space-page.html',
  styleUrl: './space-page.scss',
})
export class SpacePage {
  readonly api = inject(Api);
  private readonly dialog = inject(MatDialog);
  private readonly router = inject(Router);
  readonly cfg = inject(ConfigService).config;
  readonly id = input.required({ transform: numberAttribute });
  readonly ago = ago;

  readonly spaces = resource({ loader: () => this.api.spaces() });
  readonly space = computed(() => this.spaces.value()?.find((s) => s.id === this.id()));
  readonly children = computed(() => (this.spaces.value() ?? []).filter((s) => s.parent_id === this.id()));
  readonly photos = resource({ params: () => this.id(), loader: ({ params }) => this.api.photos(params) });
  readonly plans = resource({ params: () => this.id(), loader: ({ params }) => this.api.plans(params) });
  readonly checkins = resource({ params: () => this.id(), loader: ({ params }) => this.api.checkins(params) });

  /** The plan shown: the one picked, else the newest that isn't archived. */
  readonly pickedPlan = signal<number | null>(null);
  readonly planId = computed(() => this.pickedPlan() ?? this.plans.value()?.find((p) => p.status !== 'archived')?.id ?? null);
  readonly plan = resource({
    params: () => this.planId() ?? undefined,
    loader: ({ params }) => this.api.plan(params),
  });
  readonly showPlanForm = signal(false);
  readonly reviewQueued = signal(false);
  readonly busy = signal(false);

  readonly doneIds = computed(() => new Set((this.plan.value()?.tasks ?? []).filter((t) => t.status === 'done' || t.status === 'skipped').map((t) => t.id)));
  readonly openTasks = computed(() => (this.plan.value()?.tasks ?? []).filter((t) => t.status !== 'done' && t.status !== 'skipped'));
  readonly unsent = computed(() => this.openTasks().filter((t) => !t.gameplan_task_id));
  readonly writing = computed(() => {
    const p = this.plan.value();
    return !!p && (p.job_status === 'pending' || p.job_status === 'running');
  });

  newStep = '';

  constructor() {
    // While Claude is writing the plan, check every few seconds.
    effect((onCleanup) => {
      if (!this.writing()) return;
      const timer = setInterval(() => this.plan.reload(), 4000);
      onCleanup(() => clearInterval(timer));
    });
    // Each time the plan (re)loads, refresh the space's progress numbers too.
    effect(() => {
      if (this.plan.value()) untracked(() => this.spaces.reload());
    });
  }

  blocked(t: Task) {
    return (t.depends_on ?? []).some((d) => !this.doneIds().has(d));
  }

  async createPlan(body: PlanIn) {
    this.busy.set(true);
    const plan = await this.api.createPlan(this.id(), body);
    this.busy.set(false);
    this.showPlanForm.set(false);
    this.pickedPlan.set(plan.id);
    this.plans.reload();
  }

  async setStatus(t: Task, status: 'todo' | 'doing' | 'done' | 'skipped') {
    await this.api.patchTask(t.id, { status });
    this.refresh();
  }

  async removeTask(t: Task) {
    await this.api.deleteTask(t.id);
    this.refresh();
  }

  async addStep() {
    const id = this.planId();
    if (!id || !this.newStep.trim()) return;
    await this.api.addTask(id, { title: this.newStep.trim(), est_minutes: 20, phase: 'sort', priority: 2 });
    this.newStep = '';
    this.plan.reload();
  }

  async finishPlan(status: 'done' | 'archived') {
    const id = this.planId();
    if (id) await this.api.setPlanStatus(id, status);
    this.pickedPlan.set(null);
    this.plans.reload();
  }

  async review() {
    await this.api.review(this.id());
    this.reviewQueued.set(true);
  }

  sendToGamePlan() {
    this.dialog
      .open(SendDialog, { data: { tasks: this.unsent(), area: this.cfg()?.gameplan?.area ?? 'Home' }, width: '640px', maxWidth: '96vw' })
      .afterClosed()
      .subscribe((sent) => sent && this.plan.reload());
  }

  async syncGamePlan() {
    await this.api.syncGamePlan();
    this.refresh();
  }

  async deleteSpace() {
    if (!confirm(`Delete "${this.space()?.name}"? Its plans and check-ins go too; photos and items stay, unassigned. This cannot be undone.`)) return;
    await this.api.deleteSpace(this.id());
    this.router.navigate(['/spaces']);
  }

  private refresh() {
    this.plan.reload();
    this.spaces.reload();
  }
}
