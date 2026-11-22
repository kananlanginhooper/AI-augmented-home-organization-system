import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection,
} from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { MatIconRegistry } from '@angular/material/icon';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { ConfigService, loadedConfig } from './core/config.service';
import { provideRouteReporter } from './shared/for-apps/route-reporter';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(),
    // <mat-icon> uses the Material Symbols font from the material-symbols package (styles.scss)
    provideAppInitializer(() => {
      inject(MatIconRegistry).setDefaultFontSetClass('material-symbols-outlined');
    }),
    provideAppInitializer(() => inject(ConfigService).load()),
    // Copied unchanged from the wrapper repo (ui/src/for-apps/route-reporter.ts, 71f4670).
    provideRouteReporter(() => loadedConfig.value?.frameParents ?? []),
  ],
};
