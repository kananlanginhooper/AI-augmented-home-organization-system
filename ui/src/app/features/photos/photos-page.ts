import { ChangeDetectionStrategy, Component, computed, inject, resource, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { Api, type Photo } from '../../core/api';
import { PhotoDialog } from './photo-dialog';
import { UploadZone } from './upload-zone';

@Component({
  selector: 'app-photos-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, MatButtonToggleModule, MatDialogModule, MatFormFieldModule, MatSelectModule, UploadZone],
  template: `
    <app-upload-zone [spaces]="spaces.value() ?? []" (uploaded)="reload()" />

    <div class="bar">
      <mat-form-field subscriptSizing="dynamic">
        <mat-label>Show</mat-label>
        <mat-select [ngModel]="filter()" (ngModelChange)="filter.set($event)">
          <mat-option value="all">All photos</mat-option>
          <mat-option value="unassigned">Not assigned to a space</mat-option>
          @for (s of spaces.value() ?? []; track s.id) {
            <mat-option [value]="s.id">{{ s.path }}</mat-option>
          }
        </mat-select>
      </mat-form-field>
      <span class="count">{{ photos.value()?.length ?? 0 }} photos · {{ waiting() }} waiting for Claude</span>
    </div>

    <div class="grid">
      @for (p of photos.value() ?? []; track p.id) {
        <button class="tile" (click)="open(p)" [attr.aria-label]="'Open photo ' + (p.original_name || p.id)">
          <img [src]="api.photoUrl(p)" alt="" loading="lazy" />
          <span class="tags">
            <span class="app-pill">{{ p.phase }}</span>
            @if (p.analysis) {
              <span class="app-pill" data-tone="ok">{{ itemCount(p) }} items</span>
            } @else {
              <span class="app-pill" data-tone="warn">waiting</span>
            }
          </span>
          <span class="where">{{ spaceName(p.space_id) || 'not assigned' }}</span>
        </button>
      } @empty {
        <div class="app-empty">No photos here yet.</div>
      }
    </div>
  `,
  styles: `
    .bar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--app-space-3); margin: var(--app-space-5) 0 var(--app-space-3); }
    .count { font: var(--app-text-sm); color: var(--app-muted); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--app-space-3); }
    .tile { position: relative; padding: 0; border: 1px solid var(--app-line); border-radius: var(--app-radius-m); overflow: hidden;
      background: var(--app-card); cursor: pointer; text-align: left; color: inherit; font: inherit; }
    .tile:hover { border-color: var(--app-accent); }
    .tile img { display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: cover; }
    .tags { position: absolute; top: var(--app-space-2); left: var(--app-space-2); display: flex; gap: var(--app-space-1); }
    .tags .app-pill { background: color-mix(in srgb, var(--app-card) 85%, transparent); }
    .where { display: block; padding: var(--app-space-2); font: var(--app-text-xs); color: var(--app-muted); }
  `,
})
export class PhotosPage {
  readonly api = inject(Api);
  private readonly dialog = inject(MatDialog);
  readonly filter = signal<'all' | 'unassigned' | number>('all');
  readonly spaces = resource({ loader: () => this.api.spaces() });
  readonly photos = resource({
    params: () => this.filter(),
    loader: ({ params: f }) => this.api.photos(typeof f === 'number' ? f : undefined, f === 'unassigned'),
  });
  readonly waiting = computed(() => (this.photos.value() ?? []).filter((p) => !p.analysis).length);

  spaceName(id: number | null | undefined) {
    return this.spaces.value()?.find((s) => s.id === id)?.path ?? '';
  }

  itemCount(p: Photo) {
    return ((p.analysis as { items?: unknown[] } | null)?.items ?? []).length;
  }

  reload() {
    this.photos.reload();
    this.spaces.reload();
  }

  open(photo: Photo) {
    this.dialog
      .open(PhotoDialog, { data: { photo, spaces: this.spaces.value() ?? [] }, width: '1100px', maxWidth: '96vw' })
      .afterClosed()
      .subscribe((changed) => changed && this.reload());
  }
}
