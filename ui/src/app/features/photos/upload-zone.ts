import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { Api, type Phase, type Space } from '../../core/api';

/** Drop or pick photos (phones: the camera too), choose the space and phase, upload them one by one. */
@Component({
  selector: 'app-upload-zone',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, MatButtonModule, MatFormFieldModule, MatIconModule, MatInputModule, MatProgressBarModule, MatSelectModule],
  template: `
    <div class="fields">
      <mat-form-field subscriptSizing="dynamic">
        <mat-label>Space</mat-label>
        <mat-select [(ngModel)]="spaceId">
          <mat-option [value]="null">Not sure yet</mat-option>
          @for (s of spaces(); track s.id) {
            <mat-option [value]="s.id">{{ s.path }}</mat-option>
          }
        </mat-select>
      </mat-form-field>
      <mat-form-field subscriptSizing="dynamic">
        <mat-label>Phase</mat-label>
        <mat-select [(ngModel)]="phase">
          <mat-option value="before">Before</mat-option>
          <mat-option value="progress">Progress</mat-option>
          <mat-option value="after">After</mat-option>
          <mat-option value="reference">Reference</mat-option>
        </mat-select>
      </mat-form-field>
      <mat-form-field subscriptSizing="dynamic" class="grow">
        <mat-label>Note for Claude (optional)</mat-label>
        <input matInput [(ngModel)]="caption" placeholder="e.g. the bins on the left are holiday decorations" />
      </mat-form-field>
    </div>

    @if (demo()) {
      <div class="drop off">Uploads are off in the demo.</div>
    } @else {
      <label
        class="drop"
        [class.over]="over()"
        (dragover)="$event.preventDefault(); over.set(true)"
        (dragleave)="over.set(false)"
        (drop)="drop($event)"
      >
        <mat-icon>add_a_photo</mat-icon>
        <span>Drop photos here, or <u>choose files</u></span>
        <input type="file" accept="image/*,.heic,.heif" multiple (change)="picked($event)" hidden />
      </label>
    }
    @if (busy()) {
      <mat-progress-bar mode="determinate" [value]="(done() / total()) * 100" />
      <div class="status">Uploading {{ done() }} of {{ total() }}…</div>
    } @else if (message()) {
      <div class="status">{{ message() }}</div>
    }
  `,
  styles: `
    :host { display: block; }
    .fields { display: flex; flex-wrap: wrap; gap: var(--app-space-3); margin-bottom: var(--app-space-3); }
    .grow { flex: 1 1 280px; }
    .drop { display: flex; align-items: center; justify-content: center; gap: var(--app-space-2); min-height: 96px;
      border: 2px dashed var(--app-line); border-radius: var(--app-radius-m); color: var(--app-muted); cursor: pointer;
      font: var(--app-text-md); }
    .drop.over, .drop:hover { border-color: var(--app-accent); color: var(--app-accent); }
    .drop.off { cursor: default; }
    .status { font: var(--app-text-sm); color: var(--app-muted); margin-top: var(--app-space-2); }
  `,
})
export class UploadZone {
  private readonly api = inject(Api);
  readonly spaces = input.required<Space[]>();
  readonly uploaded = output<void>();
  readonly demo = signal(this.api.demo);

  spaceId: number | null = null;
  phase: Phase = 'before';
  caption = '';
  readonly over = signal(false);
  readonly busy = signal(false);
  readonly done = signal(0);
  readonly total = signal(0);
  readonly message = signal('');

  drop(e: DragEvent) {
    e.preventDefault();
    this.over.set(false);
    this.send(Array.from(e.dataTransfer?.files ?? []));
  }

  picked(e: Event) {
    const input = e.target as HTMLInputElement;
    this.send(Array.from(input.files ?? []));
    input.value = '';
  }

  private async send(files: File[]) {
    const images = files.filter((f) => f.type.startsWith('image/') || /\.(heic|heif)$/i.test(f.name));
    if (!images.length) return;
    this.busy.set(true);
    this.total.set(images.length);
    this.done.set(0);
    let dupes = 0;
    const failed: string[] = [];
    for (const f of images) {
      try {
        const r = await this.api.upload(f, { spaceId: this.spaceId ?? undefined, phase: this.phase, caption: this.caption || undefined });
        if (r.duplicate) dupes++;
      } catch {
        failed.push(f.name);
      }
      this.done.update((n) => n + 1);
    }
    this.busy.set(false);
    const sent = images.length - failed.length - dupes;
    this.message.set(
      [`${sent} uploaded and queued for Claude`, dupes ? `${dupes} already here` : '', failed.length ? `failed: ${failed.join(', ')}` : '']
        .filter(Boolean)
        .join(' · '),
    );
    this.uploaded.emit();
  }
}
