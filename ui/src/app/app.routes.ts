import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'overview' },
  { path: 'overview', loadComponent: () => import('./features/overview/overview-page').then((m) => m.OverviewPage) },
  { path: 'photos', loadComponent: () => import('./features/photos/photos-page').then((m) => m.PhotosPage) },
  { path: 'inventory', loadComponent: () => import('./features/inventory/inventory-page').then((m) => m.InventoryPage) },
  { path: 'spaces', loadComponent: () => import('./features/spaces/spaces-page').then((m) => m.SpacesPage) },
  { path: 'spaces/:id', loadComponent: () => import('./features/spaces/space-page').then((m) => m.SpacePage) },
  { path: 'claude', loadComponent: () => import('./features/jobs/jobs-page').then((m) => m.JobsPage) },
  { path: '**', redirectTo: 'overview' },
];
