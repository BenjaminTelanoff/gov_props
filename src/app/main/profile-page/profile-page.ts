import { Component, inject, OnInit } from '@angular/core';
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

  constructor (private router: Router,) {}
  
  // Observable to hold the politician data from Firestore
  politician$: Observable<any> | undefined;
  
  // Property to hold the proposition currently being viewed in the modal
  selectedProp: any = null;

  goBack(): void {
    this.router.navigate(['/']);
  }

  ngOnInit() {
    // Get the name parameter from the URL and query Firestore by Name field
    this.politician$ = this.route.params.pipe(
      switchMap(params => {
        const name = params['name'];
        const col = collection(this.firestore, 'Politicians');
        const q = query(col, where('Name', '==', name));
        return from(getDocs(q)).pipe(
          map(snapshot => {
            if (snapshot.empty) return null;
            return snapshot.docs[0].data();
          })
        );
      }),
      map(data => {
        if (!data) return null;

        // Convert the Propositions Map into a sorted array for the table
        const propsMap = data['Propositions'] || {};
        const propsArray = Object.entries(propsMap)
          .sort(([a], [b]) => Number(a) - Number(b))
          .map(([_, value]) => value);
        
        return { ...data, propsList: propsArray };
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