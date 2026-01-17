import { Routes } from '@angular/router';

export const routes: Routes = [
   { path: '', loadComponent: () => import('./main/homepage/homepage')
    .then((mod) => mod.Homepage)},
    { 
    path: 'profile/:name', loadComponent: () => import('./main/profile-page/profile-page')
    .then((mod) => mod.ProfilePage)
    },
];
