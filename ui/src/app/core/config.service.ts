import { Injectable, inject, signal } from '@angular/core';
import { Api, type UiConfig } from './api';

/** The loaded config outside injection, for provideRouteReporter's frameParents callback. */
export const loadedConfig: { value: UiConfig | null } = { value: null };

/** Runtime config from api/config, loaded once before the app starts. */
@Injectable({ providedIn: 'root' })
export class ConfigService {
  private readonly api = inject(Api);
  readonly config = signal<UiConfig | null>(null);

  async load(): Promise<void> {
    loadedConfig.value = await this.api.config();
    this.config.set(loadedConfig.value);
  }
}
