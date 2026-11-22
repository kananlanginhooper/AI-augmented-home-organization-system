import { ChangeDetectionStrategy, Component, inject, resource } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { Api } from '../../core/api';
import { ProgressLine } from '../../shared/progress-line';
import { StatusPill, EmptyState } from '../../shared/for-apps/status';

@Component({
  selector: 'app-spaces-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StatusPill, EmptyState, FormsModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule, RouterLink, ProgressLine],
  template: `
    <form class="add" (ngSubmit)="add()">
      <mat-form-field subscriptSizing="dynamic" class="grow">
        <mat-label>New space</mat-label>
        <input matInput name="name" [(ngModel)]="name" placeholder="Garage, Hall closet, Bin 4…" />
      </mat-form-field>
      <mat-form-field subscriptSizing="dynamic">
        <mat-label>Inside</mat-label>
        <mat-select name="parent" [(ngModel)]="parentId">
          <mat-option [value]="null">(a room of its own)</mat-option>
          @for (s of spaces.value() ?? []; track s.id) {
            <mat-option [value]="s.id">{{ s.path }}</mat-option>
          }
        </mat-select>
      </mat-form-field>
      <mat-form-field subscriptSizing="dynamic">
        <mat-label>Kind</mat-label>
        <mat-select name="kind" [(ngModel)]="kind">
          <mat-option value="room">Room</mat-option>
          <mat-option value="zone">Zone (a wall, a corner, a closet)</mat-option>
          <mat-option value="container">Container (bin, shelf, drawer)</mat-option>
        </mat-select>
      </mat-form-field>
      <button mat-flat-button type="submit" [disabled]="!name.trim()">Add</button>
    </form>

    @for (s of spaces.value() ?? []; track s.id) {
      <a class="space" [routerLink]="['/spaces', s.id]" [style.margin-left.px]="depth(s.path) * 24">
        <div class="head">
          <span class="name">{{ s.name }}</span>
          <app-pill>{{ s.kind }}</app-pill>
        </div>
        @if (s.goal) {
          <div class="goal">{{ s.goal }}</div>
        }
        <app-progress-line [p]="s.progress" />
      </a>
    } @empty {
      <app-empty-state message="No spaces yet. Add the first room above." />
    }
  `,
  styles: `
    .add { display: flex; flex-wrap: wrap; align-items: center; gap: var(--app-space-3); margin-bottom: var(--app-space-4); }
    .grow { flex: 1 1 240px; }
    .space { display: block; padding: var(--app-space-3) var(--app-space-4); margin-bottom: var(--app-space-2);
      border: 1px solid var(--app-line); border-radius: var(--app-radius-m); background: var(--app-card); color: inherit; text-decoration: none; }
    .space:hover { border-color: var(--app-accent); }
    .head { display: flex; align-items: center; gap: var(--app-space-2); }
    .name { font: var(--app-text-lg); }
    .goal { font: var(--app-text-sm); color: var(--app-muted); margin-bottom: var(--app-space-2); }
    @media (max-width: 600px) { .space { margin-left: 0 !important; } }
  `,
})
export class SpacesPage {
  private readonly api = inject(Api);
  readonly spaces = resource({ loader: () => this.api.spaces() });
  name = '';
  parentId: number | null = null;
  kind: 'room' | 'zone' | 'container' = 'room';

  depth(path: string) {
    return path.split(' / ').length - 1;
  }

  async add() {
    const kind = this.parentId == null ? 'room' : this.kind === 'room' ? 'zone' : this.kind;
    await this.api.createSpace({ name: this.name.trim(), parent_id: this.parentId, kind });
    this.name = '';
    this.spaces.reload();
  }
}
