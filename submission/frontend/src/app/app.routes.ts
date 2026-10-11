import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () => import('./pages/anonymize/anonymize').then((m) => m.Anonymize),
  },
  { path: '**', redirectTo: '' },
];
