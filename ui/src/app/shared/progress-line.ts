import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import type { Progress } from '../core/api';
import { minutes, percent } from './format';

/** One line of progress for a space: a bar of minutes done, steps, decisions and photos. */
@Component({
  selector: 'app-progress-line',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="bar" [attr.aria-label]="pct() + '% of planned minutes done'">
      <span [style.width.%]="pct()"></span>
    </div>
    <div class="facts">
      @if (p().tasks_total) {
        <span>{{ p().tasks_done }}/{{ p().tasks_total }} steps · {{ done() }} of {{ total() }}</span>
      } @else {
        <span>no plan yet</span>
      }
      <span>{{ p().items_decided }}/{{ p().items_total }} items decided</span>
      <span>{{ p().photos }} photos</span>
      @if (p().latest_percent != null) {
        <span>Claude: ~{{ p().latest_percent }}% there</span>
      }
    </div>
  `,
  styles: `
    :host { display: block; }
    .bar { height: 8px; border-radius: 999px; background: var(--app-line); overflow: hidden; }
    .bar span { display: block; height: 100%; background: var(--app-accent); transition: width 0.3s; }
    .facts { display: flex; flex-wrap: wrap; gap: var(--app-space-1) var(--app-space-3); margin-top: var(--app-space-1);
      font: var(--app-text-xs); color: var(--app-muted); }
  `,
})
export class ProgressLine {
  readonly p = input.required<Progress>();
  readonly pct = computed(() => percent(this.p().minutes_done, this.p().minutes_total));
  readonly done = computed(() => minutes(this.p().minutes_done));
  readonly total = computed(() => minutes(this.p().minutes_total));
}
