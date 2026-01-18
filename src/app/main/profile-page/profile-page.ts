import { Component, inject, OnInit, DestroyRef } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { tap, shareReplay } from 'rxjs';
import { ActivatedRoute } from '@angular/router';
import { Firestore, collection, query, where, getDocs } from '@angular/fire/firestore';
import { CommonModule } from '@angular/common';
import { Observable, from, map, switchMap } from 'rxjs';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';

@Component({
  selector: 'app-profile-page',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
  ],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss',
})
export class ProfilePage implements OnInit {
  private firestore: Firestore = inject(Firestore);
  private route: ActivatedRoute = inject(ActivatedRoute);

  constructor (private router: Router, private destroyRef: DestroyRef,) {}
  
  // Observable to hold the politician data from Firestore
  politician$: Observable<any> | undefined;

  allPoliticians$: Observable<any> | undefined;
  
  private validNames: string[] = []

  // Property to hold the proposition currently being viewed in the modal
  selectedProp: any = null;

  goBack(): void {
    this.router.navigate(['/']);
  }

  toPage(person: string): void {
    if (!this.validNames.includes(person)) {
      console.warn("Person not found in list");
      return;
    }
    this.router.navigate(['/profile', person]);
  }

  ngOnInit() {
    const col = collection(this.firestore, 'Politicians');

    // 1. Fetch list of names and sync with local array
    this.allPoliticians$ = from(getDocs(col)).pipe(
      map(snapshot => snapshot.docs.map(doc => doc.data()['Name'])),
      tap(names => this.validNames = names), 
      shareReplay(1),
      takeUntilDestroyed(this.destroyRef) // Ensures no memory leaks
    );

    // Initial trigger for the names list
    this.allPoliticians$.subscribe();

    // 2. Fetch specific politician data
    this.politician$ = this.route.params.pipe(
      switchMap(params => {
        const name = params['name'];
        const q = query(col, where('Name', '==', name));
        return from(getDocs(q)).pipe(
          map(snapshot => snapshot.empty ? null : snapshot.docs[0].data())
        );
      }),
      map(data => {
        if (!data) return null;
        const propsMap = data['Propositions'] || {};
        const propsList = Object.entries(propsMap)
          .sort(([a], [b]) => Number(a) - Number(b))
          .map(([_, value]) => value);
        
        return { ...data, propsList };
      })
    );
  }
  // Open modal and prevent background scrolling
  openModal(prop: any) {
    this.selectedProp = prop;
    document.body.style.overflow = 'hidden';
  }

  // Close modal and restore scrolling
  closeModal() {
    this.selectedProp = null;
    document.body.style.overflow = 'auto';
  }

  // Logic to determine status styling
  getStatusClass(status: string): string {
    const s = status?.toLowerCase() || '';
    if (s.includes('success')) {
      return 'status-success';
    }
    if (s.includes('compromised')) {
      return 'status-compromised';
    }
    if (s.includes('failed')) {
      return 'status-failed';
    }
    return 'status-default';
  }

  // Calculate sentiment color based on percentage (battery indicator style)
  getSentimentColor(percentage: number): string {
    // Red (0-33%) -> Yellow (33-66%) -> Green (66-100%)
    if (percentage <= 33) {
      // Red: #ef5350
      return '#ef5350';
    } else if (percentage <= 66) {
      // Yellow/Orange: #ffa726
      return '#ffa726';
    } else {
      // Green: #66bb6a
      return '#66bb6a';
    }
  }
}