import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NavBar } from './features/shell/nav-bar';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, NavBar],
  template: `
    <app-nav-bar />
    <main><router-outlet /></main>
  `,
  styles: `
    :host { display: block; }
    main {
      max-width: 1400px; margin: 0 auto;
      padding: var(--app-space-4) max(var(--app-space-4), env(safe-area-inset-right))
        max(var(--app-space-4), env(safe-area-inset-bottom)) max(var(--app-space-4), env(safe-area-inset-left));
    }
    @media (max-width: 600px) { main { padding-left: max(var(--app-space-3), env(safe-area-inset-left)); padding-right: max(var(--app-space-3), env(safe-area-inset-right)); } }
  `,
})
export class App {}
