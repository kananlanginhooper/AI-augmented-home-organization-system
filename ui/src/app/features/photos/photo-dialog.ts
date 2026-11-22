import { ChangeDetectionStrategy, Component, inject, resource, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { Api, type Phase, type Photo, type Space } from '../../core/api';
import { ago, DISPOSITION_TONE } from '../../shared/format';

interface SeenItem {
  name: string;
  quantity: number;
  spot: string;
  condition: string;
  suggested_disposition: string;
  reason: string;
}
interface Analysis {
  summary: string;
  space_guess: string;
  items: SeenItem[];
  observations: { issue: string; severity: string; suggestion: string }[];
  questions: string[];
}

/** One photo: the picture, Claude's reading of it, other tools' results, and where it belongs. */
@Component({
  selector: 'app-photo-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatSelectModule],
  templateUrl: './photo-dialog.html',
  styleUrl: './photo-dialog.scss',
})
export class PhotoDialog {
  readonly api = inject(Api);
  private readonly ref = inject(MatDialogRef<PhotoDialog>);
  readonly data = inject<{ photo: Photo; spaces: Space[] }>(MAT_DIALOG_DATA);
  readonly photo = signal(this.data.photo);
  readonly evaluations = resource({ loader: () => this.api.evaluations(this.data.photo.id) });
  readonly tone = DISPOSITION_TONE;
  readonly ago = ago;
  changed = false;

  get analysis(): Analysis | null {
    return (this.photo().analysis as unknown as Analysis) ?? null;
  }

  json(v: unknown) {
    return JSON.stringify(v, null, 1);
  }

  async save(patch: { space_id?: number | null; phase?: Phase }) {
    this.photo.set(await this.api.patchPhoto(this.photo().id, patch));
    this.changed = true;
  }

  async reanalyze() {
    await this.api.analyze(this.photo().id);
    this.ref.close(true);
  }

  async remove() {
    if (!confirm('Delete this photo and its files? This cannot be undone. Items found in it stay in the inventory.')) return;
    await this.api.deletePhoto(this.photo().id);
    this.ref.close(true);
  }

  close() {
    this.ref.close(this.changed);
  }
}
