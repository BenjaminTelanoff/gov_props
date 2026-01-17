import { Component, Signal, OnInit, signal } from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import { Firestore, collection, collectionData } from '@angular/fire/firestore';
import {Observable} from 'rxjs';
import {map, startWith} from 'rxjs/operators';
import {AsyncPipe} from '@angular/common';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatInputModule} from '@angular/material/input';
import {MatFormFieldModule} from '@angular/material/form-field';


@Component({
  selector: 'app-homepage',
  imports: [
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    ReactiveFormsModule,
    AsyncPipe,
  ],
  templateUrl: './homepage.html',
  styleUrl: './homepage.scss',
})
export class Homepage implements OnInit {
  myControl = new FormControl('');
  options: Signal<string[]> = signal(['One', 'Two', 'Three']);
  filteredOptions!: Observable<string[]>;

  ngOnInit() {
    this.filteredOptions = this.myControl.valueChanges.pipe(
      startWith(''),
      map(value => this._filter(value || '')),
    );
  }

  private _filter(value: string): string[] {
    const filterValue = value.toLowerCase();

    return this.options().filter(option => option.toLowerCase().includes(filterValue));
  }

  constructor(private firestore: Firestore) {}

  getPoliticians() {
    const col = collection(this.firestore, 'politicians');
    const data$ = collectionData(col, { idField: 'id' });
    return data$;
  }
}
