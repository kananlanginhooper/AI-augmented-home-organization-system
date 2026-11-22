import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { NAV_LINKS, NavBar } from './features/shell/nav-bar';
import { BottomNav } from './shared/for-apps/tab-nav';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, NavBar, BottomNav],
  template: `
    <app-nav-bar />
    <main [class.framed]="framed"><router-outlet /></main>
    <app-bottom-nav [links]="links" />
  `,
  styles: `
    :host { display: block; }
    main {
      max-width: 1400px; margin: 0 auto;
      padding: var(--app-space-4) max(var(--app-space-4), env(safe-area-inset-right))
        max(var(--app-space-4), env(safe-area-inset-bottom)) max(var(--app-space-4), env(safe-area-inset-left));
    }
    @media (max-width: 600px) {
      main { padding-left: max(var(--app-space-3), env(safe-area-inset-left)); padding-right: max(var(--app-space-3), env(safe-area-inset-right)); }
      /* opened on its own, the bottom nav covers the last 56 px */
      main:not(.framed) { padding-bottom: calc(56px + var(--app-space-4) + env(safe-area-inset-bottom)); }
    }
  `,
})
export class App {
  readonly links = NAV_LINKS;
  readonly framed = window.parent !== window;
}
