import { ChangeDetectionStrategy, Component, inject, resource, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTableModule } from '@angular/material/table';
import { Api, DISPOSITIONS, type Item, type ItemPatch } from '../../core/api';
import { DISPOSITION_TONE } from '../../shared/format';
import { StatusPill } from '../../shared/for-apps/status';
import { StackTable } from '../../shared/for-apps/stack-table';

/** What is where: search ("where's the drill?"), review Claude's suggestions, decide what stays. */
@Component({
  selector: 'app-inventory-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [StatusPill, StackTable, 
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTableModule,
  ],
  templateUrl: './inventory-page.html',
  styleUrl: './inventory-page.scss',
})
export class InventoryPage {
  private readonly api = inject(Api);
  readonly dispositions = DISPOSITIONS;
  readonly tone = DISPOSITION_TONE;
  readonly columns = ['name', 'where', 'condition', 'disposition', 'actions'];

  readonly q = signal('');
  readonly spaceId = signal<number | null>(null);
  readonly disposition = signal('');
  readonly unconfirmed = signal(false);

  readonly spaces = resource({ loader: () => this.api.spaces() });
  readonly items = resource({
    params: () => ({ q: this.q(), spaceId: this.spaceId() ?? undefined, disposition: this.disposition(), unconfirmed: this.unconfirmed() }),
    loader: ({ params }) => this.api.items(params),
  });

  newName = '';
  newSpace: number | null = null;

  spaceName(id: number | null | undefined) {
    return this.spaces.value()?.find((s) => s.id === id)?.path ?? 'unplaced';
  }

  async decide(item: Item, disposition: string) {
    await this.api.patchItem(item.id, { disposition: disposition as ItemPatch['disposition'] });
    this.items.reload();
  }

  async confirm(item: Item) {
    await this.api.patchItem(item.id, { confirmed: true });
    this.items.reload();
  }

  async move(item: Item, spaceId: number | null) {
    await this.api.patchItem(item.id, { space_id: spaceId });
    this.items.reload();
  }

  async remove(item: Item) {
    await this.api.deleteItem(item.id);
    this.items.reload();
  }

  async add() {
    if (!this.newName.trim()) return;
    await this.api.createItem({ name: this.newName.trim(), space_id: this.newSpace, quantity: 1, disposition: 'keep' });
    this.newName = '';
    this.items.reload();
  }
}
