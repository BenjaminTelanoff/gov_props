import { Routes } from '@angular/router';

export const routes: Routes = [
   { path: '', loadComponent: () => import('./main/homepage/homepage')
    .then((mod) => mod.Homepage)},
];
