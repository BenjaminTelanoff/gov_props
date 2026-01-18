import { Component, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import {MatIconModule} from '@angular/material/icon';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {Observable} from 'rxjs';
import {map, startWith} from 'rxjs/operators';
import {AsyncPipe} from '@angular/common';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatInputModule} from '@angular/material/input';
import {MatFormFieldModule} from '@angular/material/form-field';
import { Firestore, collection, collectionData } from '@angular/fire/firestore';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-homepage',
  imports: [
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    ReactiveFormsModule,
    AsyncPipe,
    MatIconModule,
  ],
  templateUrl: './homepage.html',
  styleUrl: './homepage.scss',
})
export class Homepage implements OnInit {
  private topMatch: string | null = null;
  myControl = new FormControl('');
  filteredOptions!: Observable<string[]>;

  options = signal<string[]>([]);

  goToPage(inputValue: string | null): void {
    const destinationName = this.topMatch || inputValue;

    if (destinationName && destinationName.trim() !== '') {
      this.router.navigate(['/profile', destinationName]);
    }
  }

  constructor(
    private firestore: Firestore, 
    private router: Router,
  ) {
    const col = collection(this.firestore, 'Politicians');
    collectionData(col).pipe(
      takeUntilDestroyed(),
      map((items: any[]) => items.map(i => i.Name))
    ).subscribe((names: string[]) => {
      this.options.set(names);     
      this.myControl.setValue(this.myControl.value);
    });
  }

  private _filter(value: string): string[] {
    const filterValue = value.toLowerCase();

    return this.options().filter(option => 
      option && option.toLowerCase().includes(filterValue)
    );
  }

  ngOnInit() {
    this.filteredOptions = this.myControl.valueChanges.pipe(
      startWith(''),
      map(value => {
        const filtered = this._filter(value || '');
        // Store the first result as the "top match"
        this.topMatch = filtered.length > 0 ? filtered[0] : null;
        return filtered;
      }),
    );
  }
}
