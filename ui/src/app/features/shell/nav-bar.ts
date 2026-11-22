import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatTabsModule } from '@angular/material/tabs';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { filter } from 'rxjs';

@Component({
  selector: 'app-nav-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatTabsModule, RouterLink, RouterLinkActive],
  template: `
    <header>
      <span class="brand">Home organization</span>
      <nav mat-tab-nav-bar [tabPanel]="panel" [disablePagination]="true">
        @for (l of links; track l.path) {
          <a mat-tab-link [routerLink]="l.path" routerLinkActive #rla="routerLinkActive" [active]="rla.isActive">{{ l.label }}</a>
        }
      </nav>
    </header>
    <mat-tab-nav-panel #panel />
  `,
  styles: `
    header {
      display: flex; align-items: center; gap: var(--app-space-4); padding: 0 var(--app-space-4);
      border-bottom: 1px solid var(--app-line); background: var(--app-card);
    }
    .brand { font: var(--app-text-lg); color: var(--app-accent); white-space: nowrap; }
    nav { flex: 1; min-width: 0; }
    /* Phones: the wrapper tab already names the app, so the brand gives its room to the tabs. */
    @media (max-width: 600px) {
      header { padding: 0; gap: 0; }
      .brand { display: none; }
      .mat-mdc-tab-link { min-width: 0; padding: 0 var(--app-space-3); }
    }
  `,
})
export class NavBar {
  readonly links = [
    { path: 'overview', label: 'Overview' },
    { path: 'spaces', label: 'Spaces & plans' },
    { path: 'photos', label: 'Photos' },
    { path: 'inventory', label: 'Inventory' },
    { path: 'claude', label: 'Claude jobs' },
  ];

  constructor() {
    // The strip scrolls with a finger (no paging arrows), so bring the current tab into view after each navigation.
    const host = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
    const router = inject(Router);
    router.events
      .pipe(
        filter((e) => e instanceof NavigationEnd),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe(() => {
        const i = this.links.findIndex((l) => router.url.split(/[?#]/)[0].startsWith('/' + l.path));
        requestAnimationFrame(() =>
          host.querySelectorAll('.mat-mdc-tab-link')[i]?.scrollIntoView({ block: 'nearest', inline: 'nearest' }),
        );
      });
  }
}
