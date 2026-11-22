import { ChangeDetectionStrategy, Component } from '@angular/core';
import { TabStrip, type NavLink } from '../../shared/for-apps/tab-nav';

export const NAV_LINKS: NavLink[] = [
  { link: '/overview', label: 'Overview', icon: 'dashboard' },
  { link: '/spaces', label: 'Spaces & plans', icon: 'checklist' },
  { link: '/photos', label: 'Photos', icon: 'photo_camera' },
  { link: '/inventory', label: 'Inventory', icon: 'inventory_2' },
  { link: '/claude', label: 'Claude jobs', icon: 'smart_toy', tooltip: 'Photo analyses, plans and reviews waiting or done' },
];

@Component({
  selector: 'app-nav-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TabStrip],
  template: `
    <header>
      <span class="brand">Home organization</span>
      <app-tab-strip [links]="links" />
    </header>
  `,
  styles: `
    header {
      display: flex; align-items: center; gap: var(--app-space-4); padding: 0 var(--app-space-4);
      border-bottom: 1px solid var(--app-line); background: var(--app-card);
    }
    .brand { font: var(--app-text-lg); color: var(--app-accent); white-space: nowrap; }
    app-tab-strip { flex: 1; min-width: 0; }
    /* Phones: the wrapper tab already names the app, so the brand gives its room to the tabs. */
    @media (max-width: 600px) {
      header { padding: 0; gap: 0; }
      .brand { display: none; }
    }
  `,
})
export class NavBar {
  readonly links = NAV_LINKS;
}
