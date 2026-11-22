import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import type { PlanIn } from '../../core/api';

/** What the space should become, and the limits Claude has to plan within. */
@Component({
  selector: 'app-plan-form',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, MatButtonModule, MatFormFieldModule, MatInputModule],
  template: `
    <form (ngSubmit)="submit()">
      <mat-form-field class="full">
        <mat-label>Goal for this space</mat-label>
        <textarea matInput name="goal" rows="2" [(ngModel)]="goal" required
          placeholder="e.g. Park the car inside again, with tools on the wall and nothing on the floor"></textarea>
      </mat-form-field>
      <div class="row">
        <mat-form-field>
          <mat-label>Minutes per session</mat-label>
          <input matInput type="number" name="minutes" min="5" max="240" [(ngModel)]="minutes" />
        </mat-form-field>
        <mat-form-field class="grow">
          <mat-label>Limits and preferences (optional)</mat-label>
          <input matInput name="constraints" [(ngModel)]="constraints"
            placeholder="budget under $150, no help lifting, keep the camping gear, done before the holidays" />
        </mat-form-field>
      </div>
      <button mat-flat-button type="submit" [disabled]="!goal.trim() || busy()">{{ label() }}</button>
      <p class="hint">Claude uses this space's inventory, your decisions, what it saw in the photos and these limits.</p>
    </form>
  `,
  styles: `
    .full { width: 100%; }
    .row { display: flex; flex-wrap: wrap; gap: var(--app-space-3); }
    .grow { flex: 1 1 300px; }
    .hint { font: var(--app-text-xs); color: var(--app-muted); }
  `,
})
export class PlanForm {
  readonly initialGoal = input('');
  readonly busy = input(false);
  readonly label = input('Ask Claude for a plan');
  readonly create = output<PlanIn>();
  goal = '';
  minutes = 30;
  constraints = '';

  ngOnInit() {
    this.goal = this.initialGoal();
  }

  submit() {
    this.create.emit({ goal: this.goal.trim(), session_minutes: this.minutes, constraints: this.constraints.trim() || null });
  }
}
